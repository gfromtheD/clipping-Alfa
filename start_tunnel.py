"""Script lanzador para exponer el backend local de FastAPI mediante Cloudflare Tunnel."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def find_cloudflared() -> str | None:
    """Busca el ejecutable de cloudflared en PATH o ubicaciones estándar de Windows."""
    # 1. En PATH
    in_path = shutil.which("cloudflared")
    if in_path:
        return in_path

    # 2. Rutas conocidas en Windows
    candidates = [
        Path(r"C:\Program Files (x86)\cloudflared\cloudflared.exe"),
        Path(r"C:\Program Files\cloudflared\cloudflared.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "cloudflared" / "cloudflared.exe",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)

    return None

def main():
    exe = find_cloudflared()
    if not exe:
        print("❌ Error: cloudflared no está instalado o no se encuentra.")
        print("💡 Instálalo ejecutando: winget install --id Cloudflare.cloudflared")
        sys.exit(1)

    print("=" * 70)
    print("  🌐 INICIANDO CLOUDFLARE TUNNEL PARA CLIPPING ALFA")
    print("  🔒 Destino Local: http://localhost:8000")
    print("=" * 70)
    print("Copia la URL https://*.trycloudflare.com generada abajo y pégala en")
    print("la configuración (Settings) de https://clipping-alfa.vercel.app")
    print("=" * 70 + "\n")

    cmd = [exe, "tunnel", "--url", "http://localhost:8000"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 Túnel detenido.")

if __name__ == "__main__":
    main()
