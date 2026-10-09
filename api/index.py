import os
import sys

# Add the backend directory to the sys path so imports inside backend work
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from backend.main import app
