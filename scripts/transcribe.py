from pathlib import Path
import argparse

from faster_whisper import WhisperModel


parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--language", choices=["en", "es"], required=True)
args = parser.parse_args()

video = Path(args.input)
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

if not video.exists():
    raise FileNotFoundError(f"No existe el vídeo: {video}")

model = WhisperModel(
    "small",
    device="cuda",
    compute_type="float16",
)

print(f"Transcribiendo con GPU: {video.name}")

segments, _ = model.transcribe(
    str(video),
    language=args.language,
    beam_size=5,
    vad_filter=False,
    condition_on_previous_text=True,
)

text = "\n".join(
    f"[{segment.start:.2f} - {segment.end:.2f}] {segment.text.strip()}"
    for segment in segments
)

output_file = output_dir / f"{video.stem}_{args.language}.txt"
output_file.write_text(text, encoding="utf-8")

print(f"Guardado: {output_file}")
print("Proceso terminado")