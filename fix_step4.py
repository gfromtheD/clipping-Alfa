from pathlib import Path

p = Path("scripts/process_video.py")
text = p.read_text(encoding="utf-8")

old = "def has_final_clips(video_stem):\n    final_dir = output_dir / \"subtitled\" / video_stem\n\n\n    if not final_dir.exists():\n        return False\n\n\n    return any(final_dir.glob(\"*_subtitled.mp4\"))"

new = "def has_final_clips(video_stem):\n    final_dir = output_dir / \"subtitled\" / video_stem\n    clips_dir = output_dir / \"clips\" / video_stem\n\n    if not final_dir.exists() or not clips_dir.exists():\n        return False\n\n    expected = list(clips_dir.glob(\"clip_*.mp4\"))\n    if not expected:\n        return False\n\n    produced = list(final_dir.glob(\"*_subtitled.mp4\"))\n    if len(produced) < len(expected):\n        return False\n\n    return all(f.stat().st_size > 0 for f in produced)"

if old not in text:
    raise SystemExit("No se encontro el bloque esperado, revisar manualmente.")

p.write_text(text.replace(old, new), encoding="utf-8")
print("OK: has_final_clips reemplazada")
