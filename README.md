# clipping-Alfa

Pipeline local para detectar fragmentos, crear clips verticales y generar subtítulos dinámicos sincronizados. La selección actual es heurística; no integra LLMs.

## Ejecutar

Desde PowerShell, el comando único recomendado usa el intérprete exacto de `.venv`:

```powershell
.\run_pipeline.ps1 -Language auto -InputVideo .\input\prueba.mp4
```

Para contenido que deba ser español, sustituye `auto` por `es`. El pipeline detecta primero el idioma y falla de forma segura si no coincide; así evita producir subtítulos españoles sobre un vídeo inglés. Para procesar todos los vídeos compatibles de `input/`, omite `-InputVideo`.

Equivalente sin el envoltorio de PowerShell:

```powershell
.\.venv\Scripts\python.exe .\scripts\process_video.py --language auto --input .\input\prueba.mp4
```

Opciones relevantes: `--model small`, `--device cuda`, `--compute-type float16`, `--max-clips 8`, `--min-duration 18`, `--max-duration 45` y `--subtitle-margin-ratio 0.27`. La transcripción usa el modo secuencial de Faster-Whisper: en esta configuración evita que un VAD o ventanas por lotes descarten locución tenue; por ello no expone un tamaño de lote ficticio. Si el material ya trae subtítulos quemados, aumenta el margen (por ejemplo, `0.32`) para separar visualmente la nueva capa; no se eliminan subtítulos incrustados del original. Para limpiar ejecuciones antiguas fallidas, usa `--prune-work-days 30` (borra de `output/.work` los directorios cuyo `state.json` no se modificó en los últimos 30 días).

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Los tests de lógica (`tests/test_logic.py`) no requieren GPU ni FFmpeg. El de integración (`tests/test_integration.py`) genera un MP4 sintético con FFmpeg y sustituye las etapas de IA por dobles para verificar la publicación atómica, el registro v2, el control negativo de subtítulos y el salto de resultados ya válidos.

## Salidas y tolerancia a fallos

Cada ejecución trabaja primero en `output/.work/`. Si las cuatro etapas validan sus artefactos, se publica un único directorio inmutable en `output/videos/<id>/` mediante un renombrado atómico. Un fallo deja el estado y el log en `.work`, pero nunca publica una salida parcial ni actualiza `output/processed_videos.v2.json` como completada.

Cada salida final contiene:

- `transcript.json`: transcripción de Faster-Whisper, idioma detectado, parámetros y métricas de calidad.
- `alignment.json`: las palabras y timestamps producidos por WhisperX al alinear **el mismo texto** de `transcript.json`. Esta etapa precede a la selección: la selección usa las palabras alineadas para construir ventanas de clip exactas.
- `selection.json`: rangos, texto y puntuación de los clips seleccionados. La selección (heurística v2) genera ventanas de duración válida sobre las palabras alineadas y elige con beam search sin solapamientos.
- `clips/`: clips 1080x1920 con audio.
- `subtitles/`: un `.ass` y un `*_subtitled.mp4` por clip.
- `manifest.json` y `run.log`: estado final verificable y trazabilidad.
- `FINAL_OUTPUTS.txt`: lista explícita de los MP4 que se deben abrir. Los de `clips/` son intermedios sin subtítulos; los finales están en `subtitles/*_subtitled.mp4`.

Antes de publicar, el pipeline abre un fotograma dentro de cada diálogo y compara píxeles de la banda de subtítulos entre el clip base, una recodificación de control sin ASS y el MP4 subtitulado. La recodificación sin subtítulos mide el ruido de píxeles (control negativo); si el cambio provocado por el ASS no supera el máximo entre un mínimo absoluto y el ruido multiplicado, la etapa falla aunque existan el ASS y el MP4.

Los directorios históricos `output/clips`, `output/subtitled`, `output/whisperx` y el registro antiguo `output/processed_videos.json` se conservan y no son consumidos por el nuevo pipeline.

Los scripts antiguos `transcribe.py`, `batch_clips.py`, `make_clip.py`, `add_subtitles.py` y `fix_step4.py` no forman parte de la ruta de ejecución. En especial, no ejecutes `fix_step4.py`: es un reemplazo textual puntual heredado, no un mecanismo seguro de mantenimiento.

## Dependencias

`requirements.txt` declara las dependencias directas y `requirements.lock.txt` fija el entorno actualmente probado de Python 3.11/CUDA 12.6. No instales paquetes durante una ejecución normal. Para reconstruir el entorno, usa primero el lockfile con el índice CUDA correspondiente y valida `torch.cuda.is_available()` antes de procesar.

También se requiere `ffmpeg` y `ffprobe` en `PATH`, con filtro `ass`/libass. El pipeline mantiene `libx264`; no usa NVENC sin una prueba explícita de compatibilidad y calidad.

## Criterio de calidad de transcripción

Antes de cambiar modelo, VAD o parámetros, compara en un vídeo de referencia conocido:

1. idioma detectado y probabilidad;
2. texto frente a una transcripción de referencia;
3. confianza media (`avg_logprob`) y repetición anómala de trigramas;
4. cobertura de palabras alineadas en cada rango seleccionado;
5. duración, resolución y presencia de audio de cada MP4 final.

El manifiesto y los JSON permiten repetir exactamente la comparación con la misma configuración.
