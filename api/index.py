"""Vercel Serverless Function entry point for FastAPI backend."""

import os
import sys
from pathlib import Path

# Ensure api and scripts directories are on python path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

for path in [str(CURRENT_DIR), str(PROJECT_ROOT), str(SCRIPTS_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from api.main import app

# Vercel looks for 'app' ASGI handler
__all__ = ["app"]
