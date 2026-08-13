from pathlib import Path
import argparse
import json
import re
import subprocess


PAUSE_SECONDS = 0.55
MAX_WORDS_PER_BLOCK = 5


def ass_time(seconds):
    seconds = max(0, float(seconds))
    total_centiseconds = round(seconds * 100)

    hours = total_centiseconds // 360000
    total_centiseconds %= 360000

    minutes = total_centiseconds // 6000
    total_centiseconds %= 6000

    secs = total_centiseconds // 100
    centiseconds = total_centiseconds % 100

    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def ass_safe_text(text):
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def get_video_size(video_path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        str(video_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    width, height = result.stdout.strip().split("x")
    return int(width), int(height)


def group_words(words):
    groups = []
    current_group = []

    for word_data in words:
        word = word_data["word"].strip()
        start = float(word_data["start"])
        end = float(word_data["end"])

        if not word:
            continue

        if current_group:
            previous_end = current_group[-1]["end"]
            pause = start - previous_end
            previous_word = current_group[-1]["word"]

            should_split = (
                pause >= PAUSE_SECONDS
                or len(current_group) >= MAX_WORDS_PER_BLOCK
                or (
                    previous_word.endswith((".", "!", "?", ",", ";", ":"))
                    and len(current_group) >= 2
                )
            )

            if should_split:
                groups.append(current_group)
                current_group = []

        current_group.append(
            {
                "word": word,
                "start": start,
                "end": end,
            }
        )

    if current_group:
        groups.append(current_group)

    return groups


parser = argparse.ArgumentParser()
parser.add_argument("--clips", required=True)
parser.add_argument("--transcript", required=True)
parser.add_argument("--whisperx-json", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

clips_dir = Path(args.clips)
transcript_path = Path(args.transcript)
json_path = Path(args.whisperx_json)
output_dir = Path(args.output)

output_dir.mkdir(parents=True, exist_ok=True)

if not clips_dir.exists():
    raise FileNotFoundError(f"No existe la carpeta de clips: {clips_dir}")

if not transcript_path.exists():
    raise FileNotFoundError(f"No existe la transcripción: {transcript_path}")

if not json_path.exists():
    raise FileNotFoundError(f"No existe el JSON de WhisperX: {json_path}")

pattern = re.compile(
    r"\[(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\]\s*(.+)"
)

transcript_lines = transcript_path.read_text(
    encoding="utf-8"
).splitlines()

clip_ranges = []

for line in transcript_lines:
    match = pattern.match(line.strip())

    if match:
        start, end, text = match.groups()
        clip_ranges.append(
            {
                "start": float(start),
                "end": float(end),
                "text": text.strip(),
            }
        )

with json_path.open(encoding="utf-8") as file:
    whisperx_data = json.load(file)

all_words = []

for segment in whisperx_data.get("segments", []):
    for word_data in segment.get("words", []):
        if (
            "word" in word_data
            and "start" in word_data
            and "end" in word_data
        ):
            all_words.append(
                {
                    "word": word_data["word"],
                    "start": float(word_data["start"]),
                    "end": float(word_data["end"]),
                }
            )

if not all_words:
    raise ValueError(
        "WhisperX no ha encontrado palabras con timestamps en el JSON."
    )

skipped_clips = []

for index, clip_range in enumerate(clip_ranges, start=1):
    clip = clips_dir / f"clip_{index:02d}.mp4"
    ass_file = output_dir / f"clip_{index:02d}.ass"
    output_video = output_dir / f"clip_{index:02d}_subtitled.mp4"

    if not clip.exists():
        print(f"No existe el clip: {clip}")
        skipped_clips.append(clip.name)
        continue

    clip_start = clip_range["start"]
    clip_end = clip_range["end"]

    clip_words = []

    for word in all_words:
        overlaps_clip = (
            word["end"] > clip_start
            and word["start"] < clip_end
        )

        if overlaps_clip:
            clip_words.append(
                {
                    "word": word["word"],
                    "start": max(0, word["start"] - clip_start),
                    "end": min(clip_end - clip_start, word["end"] - clip_start),
                }
            )

    if not clip_words:
        print(f"No se encontraron palabras para: {clip.name}")
        skipped_clips.append(clip.name)
        continue

    width, height = get_video_size(clip)
    subtitle_margin = max(130, int(height * 0.16))
    font_size = max(42, int(height * 0.06))
    outline_size = max(3, int(font_size * 0.07))
    shadow_size = max(1, int(font_size * 0.03))

    subtitle_groups = group_words(clip_words)

    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        (
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,"
            "OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,"
            "ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
            "Alignment,MarginL,MarginR,MarginV,Encoding"
        ),
        (
            f"Style: Social,Arial,{font_size},&H00FFFFFF,&H000000FF,"
            f"&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,"
            f"{outline_size},{shadow_size},2,80,80,{subtitle_margin},1"
        ),
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]

    for group in subtitle_groups:
        start_time = group[0]["start"]
        end_time = group[-1]["end"]
        text = " ".join(item["word"] for item in group)

        ass_lines.append(
            "Dialogue: 0,"
            f"{ass_time(start_time)},"
            f"{ass_time(end_time)},"
            "Social,,0,0,0,,"
            f"{ass_safe_text(text)}"
        )

    ass_file.write_text(
        "\n".join(ass_lines),
        encoding="utf-8-sig",
    )

    relative_ass_path = ass_file.as_posix()

    subtitle_filter = (
        f"ass=filename='{relative_ass_path}'"
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(clip),
            "-vf",
            subtitle_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output_video),
        ],
        check=True,
    )

    print(f"Subtítulos dinámicos añadidos: {output_video.name}")

if skipped_clips:
    raise SystemExit(
        "Clips omitidos, no se generaron todos los subtitulados: "
        + ", ".join(skipped_clips)
    )

print("Proceso terminado")
