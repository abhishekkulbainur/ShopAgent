"""FastAPI app. No API keys or external services are used anywhere. User queries are never stored."""
import logging, os, time
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pipeline import run, engine, public
from evaluation import evaluate

log = logging.getLogger("footwear"); app = FastAPI(title="AI Shopping Agent - Footwear"); HITS = defaultdict(list)

# Configure CORS for production (allow configured frontend or everything if not set)
FRONTEND_ORIGIN = os.getenv("FRONTEND_URL", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
FRONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

@app.exception_handler(Exception)
async def safe_errors(request: Request, exc: Exception):      # safe error handling: details go to the server log, never to the user
    log.exception("unhandled error"); return JSONResponse({"status": "error", "message": "Something went wrong. Please try again."}, status_code=500)

@app.post("/api/search")
async def search(request: Request, body: dict):
    ip = request.client.host if request.client else "x"; n = time.time(); HITS[ip] = [t for t in HITS[ip] if n - t < 60] + [n]
    if len(HITS[ip]) > 60: raise HTTPException(429, "Too many requests. Please slow down.")
    return run(body.get("query"))

@app.get("/api/product/{pid}")
def product(pid: int):
    p = engine().by_id.get(pid)
    if not p: raise HTTPException(404, "Product not found")
    return public(p)

@app.get("/api/health")
def health():
    E = engine(); return {"products": len(E.products), "semantic_engine": E.sem.name, "secrets_required": False, "queries_stored": 0}

@app.get("/api/catalogue")
def catalogue():
    E = engine(); from collections import Counter
    return {"size": len(E.products), "by_type": Counter(p["product_type"] for p in E.products), "source": "Myntra India (CC0), May 2023 snapshot",
            "colour_known": round(sum(1 for p in E.products if p["colour"]) / len(E.products), 3),
            "gender_known": round(sum(1 for p in E.products if p["gender"]) / len(E.products), 3)}

@app.get("/api/eval")
def eval_endpoint(): return evaluate()

@app.get("/api/featured")
def featured():
    E = engine()
    types = ["running", "sneakers", "boots", "formal", "sandals", "walking"]
    res = {}
    for t in types:
        candidates = [public(p) for p in E.products if p.get("product_type") == t and p.get("image_url") and (p.get("rating") or 0) >= 3.5]
        candidates.sort(key=lambda x: (x.get("rating") or 0) * ((x.get("rating_count") or 1) ** 0.5), reverse=True)
        res[t] = candidates[:6]
    return res

if os.path.exists(os.path.join(FRONT, "index.html")): app.mount("/", StaticFiles(directory=FRONT, html=True), name="front")
