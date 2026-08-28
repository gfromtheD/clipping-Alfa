from pathlib import Path
import argparse
import re
import subprocess
import sys


MIN_DURATION = 18
MAX_DURATION = 45
DEFAULT_MAX_CLIPS = 8

HOOK_WORDS = {
    "secret", "truth", "mistake", "mistakes", "problem", "problems",
    "important", "warning", "never", "always", "best", "worst",
    "imagine", "remember", "listen", "look", "wait", "why", "how",
    "because", "but", "however", "actually", "incredible", "crazy",
    "shocking", "surprising", "finally", "lesson", "learned",
    "secreto", "verdad", "error", "errores", "problema", "problemas",
    "importante", "cuidado", "nunca", "siempre", "mejor", "peor",
    "imagina", "recuerda", "escucha", "mira", "espera", "porque",
    "pero", "increíble", "sorprendente", "finalmente", "lección",
}

WEAK_STARTS = (
    "hello",
    "hi ",
    "welcome",
    "thank you",
    "thanks",
    "hola",
    "bienvenidos",
    "gracias",
)


def score_candidate(candidate):
    text = candidate["text"].strip().lower()
    duration = candidate["end"] - candidate["start"]
    word_count = len(re.findall(r"\b[\w']+\b", text))

    score = 0

    if 22 <= duration <= 38:
        score += 4
    elif MIN_DURATION <= duration <= MAX_DURATION:
        score += 2

    if 35 <= word_count <= 95:
        score += 3

    if "?" in text:
        score += 3

    if "!" in text:
        score += 2

    hook_hits = sum(
        1
        for hook in HOOK_WORDS
        if re.search(rf"\b{re.escape(hook)}\b", text)
    )

    score += min(hook_hits, 4) * 2

    if any(text.startswith(start) for start in WEAK_STARTS):
        score -= 4

    return score


def overlaps(candidate, selected):
    for chosen in selected:
        if (
            candidate["start"] < chosen["end"]
            and candidate["end"] > chosen["start"]
        ):
            return True

    return False


parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--transcript", required=True)
parser.add_argument("--output-dir", default="output/clips")
parser.add_argument("--max-clips", type=int, default=DEFAULT_MAX_CLIPS)
args = parser.parse_args()

video_path = Path(args.input)
transcript_path = Path(args.transcript)
output_dir = Path(args.output_dir)

if not video_path.exists():
    raise FileNotFoundError(f"No existe el vídeo: {video_path}")

if not transcript_path.exists():
    raise FileNotFoundError(
        f"No existe la transcripción: {transcript_path}"
    )

output_dir.mkdir(parents=True, exist_ok=True)

pattern = re.compile(
    r"\[(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\]\s*(.+)"
)

segments = []

for line in transcript_path.read_text(encoding="utf-8").splitlines():
    match = pattern.match(line.strip())

    if not match:
        continue

    start, end, text = match.groups()
    text = text.strip()

    if text:
        segments.append(
            {
                "start": float(start),
                "end": float(end),
                "text": text,
            }
        )

if not segments:
    raise ValueError("La transcripción no contiene segmentos válidos.")

candidates = []

for start_index in range(len(segments)):
    selected_segments = []
    candidate_start = segments[start_index]["start"]

    for segment in segments[start_index:]:
        selected_segments.append(segment)
        candidate_end = segment["end"]
        duration = candidate_end - candidate_start

        if duration > MAX_DURATION:
            break

        if duration >= MIN_DURATION:
            candidate_text = " ".join(
                item["text"] for item in selected_segments
            )

            candidate = {
                "start": candidate_start,
                "end": candidate_end,
                "text": candidate_text,
            }

            candidate["score"] = score_candidate(candidate)
            candidates.append(candidate)
            break

if not candidates:
    raise ValueError(
        f"No se pudieron crear candidatos de al menos {MIN_DURATION} segundos."
    )

candidates.sort(
    key=lambda candidate: (
        candidate["score"],
        candidate["end"] - candidate["start"],
    ),
    reverse=True,
)

best_candidates = []

for candidate in candidates:
    if not overlaps(candidate, best_candidates):
        best_candidates.append(candidate)

    if len(best_candidates) >= args.max_clips:
        break

best_candidates.sort(key=lambda candidate: candidate["start"])

if not best_candidates:
    raise ValueError("No se han seleccionado clips.")

index_lines = []

for index, candidate in enumerate(best_candidates, start=1):
    output = output_dir / f"clip_{index:02d}.mp4"

    print(
        f"Creando clip {index}/{len(best_candidates)} | "
        f"Puntuación: {candidate['score']} | "
        f"{candidate['start']:.2f}s - {candidate['end']:.2f}s"
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/make_clip.py",
            "--input",
            str(video_path),
            "--start",
            str(candidate["start"]),
            "--end",
            str(candidate["end"]),
            "--output",
            str(output),
        ],
        check=True,
    )

    index_lines.append(
        f"clip_{index:02d}.mp4 | "
        f"score={candidate['score']} | "
        f"[{candidate['start']:.2f} - {candidate['end']:.2f}] "
        f"{candidate['text']}"
    )

(output_dir / "index.txt").write_text(
    "\n\n".join(index_lines),
    encoding="utf-8",
)

selected_transcript_lines = [
    f"[{candidate['start']:.2f} - {candidate['end']:.2f}] "
    f"{candidate['text']}"
    for candidate in best_candidates
]

(output_dir / "selected_transcript.txt").write_text(
    "\n".join(selected_transcript_lines),
    encoding="utf-8",
)

print(
    f"\n{len(best_candidates)} mejores clips creados en: {output_dir}"
)