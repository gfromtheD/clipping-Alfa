"""Lanzador del servidor web FastAPI y UI de Clipping Alfa."""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "api"))

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("  [*] Iniciando servidor de Clipping Alfa Web UI")
    print("  [*] URL: http://localhost:8000")
    print("=" * 60)

    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
