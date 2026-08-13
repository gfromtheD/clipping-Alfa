from pathlib import Path
import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--start", type=float, required=True)
parser.add_argument("--end", type=float, required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

Path(args.output).parent.mkdir(parents=True, exist_ok=True)

duration = args.end - args.start

command = [
    "ffmpeg",
    "-y",
    "-ss", str(args.start),
    "-i", args.input,
    "-t", str(duration),
    "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "23",
    "-c:a", "aac",
    "-b:a", "128k",
    args.output,
]

subprocess.run(command, check=True)
print(f"Clip creado: {args.output}")