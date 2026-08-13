from pathlib import Path
import argparse
import json
import subprocess
import sys
import shutil


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi"}

parser = argparse.ArgumentParser()
parser.add_argument("--language", choices=["en", "es"], default="en")
args = parser.parse_args()

input_dir = Path("input")
output_dir = Path("output")
registry_path = output_dir / "processed_videos.json"

output_dir.mkdir(exist_ok=True)

if not input_dir.exists():
    raise FileNotFoundError(f"No existe la carpeta: {input_dir}")

if registry_path.exists():
    processed_videos = json.loads(
        registry_path.read_text(encoding="utf-8")
    )
else:
    processed_videos = {}


def video_signature(video_path):
    stat = video_path.stat()

    return {
        "size": stat.st_size,
        "modified": stat.st_mtime_ns,
    }


def has_final_clips(video_stem):
    final_dir = output_dir / "subtitled" / video_stem
    clips_dir = output_dir / "clips" / video_stem

    if not final_dir.exists() or not clips_dir.exists():
        return False

    expected = list(clips_dir.glob("clip_*.mp4"))
    if not expected:
        return False

    produced = list(final_dir.glob("*_subtitled.mp4"))
    if len(produced) < len(expected):
        return False

    return all(f.stat().st_size > 0 for f in produced)



def save_registry():
    tmp_path = registry_path.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(processed_videos, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp_path.replace(registry_path)



videos = sorted(
    video
    for video in input_dir.iterdir()
    if video.is_file() and video.suffix.lower() in VIDEO_EXTENSIONS
)

if not videos:
    print("No hay vídeos compatibles en la carpeta input.")
    raise SystemExit(0)

pending_videos = []

for video in videos:
    signature = video_signature(video)
    previous = processed_videos.get(video.name)

    same_file = previous == signature
    already_has_output = has_final_clips(video.stem)

    if same_file and already_has_output:
        print(f"Omitido, ya procesado: {video.name}")
        continue

    if previous is None and already_has_output:
        processed_videos[video.name] = signature
        print(f"Registrado como ya procesado: {video.name}")
        continue

    pending_videos.append(video)

save_registry()

if not pending_videos:
    print("\nNo hay vídeos nuevos ni modificados para procesar.")
    raise SystemExit(0)

for video in pending_videos:
    stem = video.stem

    transcript = output_dir / f"{stem}_{args.language}.txt"
    clips_dir = output_dir / "clips" / stem
    selected_transcript = clips_dir / "selected_transcript.txt"
    whisperx_dir = output_dir / "whisperx" / stem
    whisperx_json = whisperx_dir / f"{stem}.json"
    subtitled_dir = output_dir / "subtitled" / stem

    for stale_dir in (clips_dir, whisperx_dir, subtitled_dir):
        if stale_dir.exists():
            shutil.rmtree(stale_dir)

    clips_dir.mkdir(parents=True, exist_ok=True)
    whisperx_dir.mkdir(parents=True, exist_ok=True)
    subtitled_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print(f"Procesando: {video.name}")
    print("=" * 60)

    print("\n[1/4] Generando transcripción...")
    subprocess.run(
        [
            sys.executable,
            "scripts/transcribe.py",
            "--input",
            str(video),
            "--language",
            args.language,
        ],
        check=True,
    )

    print("\n[2/4] Seleccionando y creando los 8 mejores clips...")
    subprocess.run(
        [
            sys.executable,
            "scripts/batch_clips.py",
            "--input",
            str(video),
            "--transcript",
            str(transcript),
            "--output-dir",
            str(clips_dir),
            "--max-clips",
            "8",
        ],
        check=True,
    )

    if not selected_transcript.exists():
        raise FileNotFoundError(
            f"No se creó la transcripción de clips seleccionados: "
            f"{selected_transcript}"
        )

    print("\n[3/4] Obteniendo timestamps por palabra con WhisperX...")
    subprocess.run(
        [
            str(Path(sys.executable).parent / "whisperx.exe"),
            str(video),
            "--model",
            "tiny",
            "--language",
            args.language,
            "--device",
            "cuda",
            "--compute_type",
            "float16",
            "--batch_size",
            "1",
            "--output_dir",
            str(whisperx_dir),
            "--output_format",
            "json",
        ],
        check=True,
    )

    if not whisperx_json.exists():
        raise FileNotFoundError(
            f"WhisperX no creó el JSON esperado: {whisperx_json}"
        )

    print("\n[4/4] Añadiendo subtítulos dinámicos...")
    subprocess.run(
        [
            sys.executable,
            "scripts/add_subtitles.py",
            "--clips",
            str(clips_dir),
            "--transcript",
            str(selected_transcript),
            "--whisperx-json",
            str(whisperx_json),
            "--output",
            str(subtitled_dir),
        ],
        check=True,
    )

    processed_videos[video.name] = video_signature(video)
    save_registry()

    print(f"\nCompletado: {video.name}")
    print(f"Vídeos finales: {subtitled_dir}")


print("\nTodos los vídeos pendientes han sido procesados.")
