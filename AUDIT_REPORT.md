# Informe de auditoría — 2026-08-11

## Diagnóstico principal

`input/prueba.mp4` (52,16 s, AAC estéreo 44,1 kHz, 32 kb/s) contiene locución inglesa. La detección automática de Faster-Whisper `small` devolvió `en` con probabilidad 0,946; con `--language en` generó cinco segmentos coherentes. La ejecución anterior lo forzó a `es` y luego WhisperX lo volvió a transcribir con `tiny`, también forzado a español. El JSON de WhisperX muestra la alucinación/repetición `de la ciudad…` y palabras de baja confianza. Por tanto, no era un fallo de CUDA ni únicamente del modelo: era la combinación de idioma erróneo, segunda transcripción independiente y `tiny`.

La alineación programática de WhisperX sobre los cinco segmentos de Faster-Whisper produjo 55 palabras con tiempos. Así se verificó que WhisperX sirve como alineador sin volver a ser una segunda fuente de texto.

Se detectó además un aviso de TorchCodec/Pyannote: `torchcodec 0.7.0` no carga sus DLL con el stack actual de PyTorch/FFmpeg. Las pruebas de WhisperX finalizaron correctamente porque el flujo de audio usado por WhisperX siguió funcionando; no se ha instalado ni cambiado TorchCodec sin una matriz de compatibilidad. El VAD Silero se probó y recuperó menos segmentos que el comportamiento actual, por lo que no se adopta como arreglo.

## Problemas críticos corregidos

- Rutas relativas a CWD y llamadas a scripts con rutas no deterministas.
- Borrado recursivo de resultados previos antes de saber si la nueva ejecución terminaría bien.
- Registro de vídeos basado en nombre/tamaño/fecha y marcado posible antes de validar el resultado completo.
- Texto para seleccionar clips (`small`) distinto del texto usado para subtítulos (`tiny`/WhisperX).
- Publicación de clips y subtítulos parciales directamente en los directorios finales.
- Falta de contratos JSON y validaciones de transcripción, alineación, vídeo vertical, audio, duración y cobertura de subtítulos.

## Problemas importantes corregidos o contenidos

- El idioma solicitado ahora se valida contra detección automática; una discrepancia falla sin publicar.
- Modelo, dispositivo, tipo de cálculo, calidad mínima, duración y codificación están centralizados y registrados.
- La transcripción usa el modo secuencial de Faster-Whisper; se descartó el lote artificial porque para vídeos de más de 30 s obliga a rangos/VAD y empeora la segmentación de la locución de referencia.
- FFmpeg y ffprobe se resuelven de forma explícita; se verifica soporte de filtro `ass` y se conserva `libx264`.
- La publicación exige ahora una verificación visual por píxeles en una ventana con diálogo, además de validar ASS, `Dialogue`, vídeo, audio y duración.
- La selección explora más de un final posible por inicio, evita solapamientos y conserva sus decisiones en JSON.
- Se añadió un manifiesto directo de dependencias junto al lockfile existente.

## Problemas menores y pendientes

- La selección sigue siendo heurística por palabras gancho; es intencional hasta integrar un LLM en una fase posterior.
- El recorte es un crop centrado, sin detección de rostro/sujeto.
- TorchCodec debe resolverse en una tarea separada con una combinación oficialmente compatible de TorchCodec, PyTorch y FFmpeg; no ha impedido las pruebas actuales.
- La calidad de audio de `prueba.mp4` es baja (AAC HE, 32 kb/s) y limita cualquier ASR. El pipeline ahora lo expone mediante métricas y validaciones, no intenta “corregir” texto de forma frágil.
- `prueba.mp4` ya contiene subtítulos quemados. El nuevo ASS se configura más arriba (`--subtitle-margin-ratio`) para reducir la colisión visual, pero retirar texto integrado en los píxeles requiere una futura etapa específica de detección/OCR e inpainting.
- Los scripts heredados siguen presentes por conservación (`transcribe.py`, `batch_clips.py`, `make_clip.py`, `add_subtitles.py` y especialmente `fix_step4.py`). No los invoca el nuevo punto de entrada; `fix_step4.py` usa sustitución textual puntual y no debe ejecutarse como herramienta de mantenimiento.

## Qué se conserva

- Python 3.11.9, CUDA detectada por PyTorch 2.8.0+cu126, `device=cuda` y `float16` para IA.
- Faster-Whisper `small` como base inicial verificable.
- WhisperX para alineación por palabra.
- FFmpeg con `libx264`, AAC, MP4 vertical 1080x1920 y subtítulos ASS incrustados.
- Vídeos y resultados históricos, sin borrar ni sobrescribir.

## Qué se reescribió

El antiguo orquestador fue reemplazado por un único punto de entrada y `scripts/pipeline_core.py`. Los scripts antiguos quedan respaldados y se dejan fuera del flujo normal para no mezclar formatos heredados con artefactos nuevos.

## Plan por fases

1. **Base estable (aplicada):** contrato JSON único, estado por etapa, publicación atómica, registro v2, validaciones y prueba de fallo.
2. **Calidad operativa:** corpus de referencia español/inglés, métricas WER/CER, prueba de audio y decisión documentada de modelo/VAD/TorchCodec.
3. **Edición visual:** seguimiento de sujeto, plantillas de estilo y pruebas de rendimiento/NVENC si una medición justifica el cambio.
4. **Selección semántica:** añadir LLM como una etapa nueva que lea `transcript.json`/`selection.json`, sin alterar los contratos de transcripción, alineación o publicación.

## Criterios para declarar el pipeline estable

- Una ejecución idéntica reutiliza sólo una salida final con manifiesto válido.
- Ningún error intermedio genera directorio final ni estado `completed` en el registro.
- Cada salida final tiene transcripción, selección, alineación, log, manifiesto, clips y un ASS/MP4 subtitulado por clip.
- Todos los MP4 finales son 1080x1920, contienen audio y su duración coincide con la selección dentro de 0,75 s.
- El idioma detectado coincide con el solicitado, o se usa `auto` con la detección guardada.
- Las etapas de IA registran CUDA activa y la alineación aporta al menos dos palabras a cada clip seleccionado.

## Actualización 2026-08-13 — endurecimiento

- Etapa de alineación reordenada antes de la selección: `select_clips` ya no depende de los límites de segmentos de Whisper, construye ventanas exactas sobre las palabras alineadas (`word_windows`) y elige sin solapamientos con beam search (`beam_select`). Método de selección: `heuristic-v2-word-windows-beam`.
- `config_fingerprint` ahora incluye toda la heurística (`SELECTION_HEURISTIC`: palabras gancho, pesos de puntuación, inicios débiles); se subió `PIPELINE_REVISION` a 4. Cambiar la heurística invalida automáticamente los resultados en caché.
- Verificación visual de subtítulos con control negativo: cada clip se recodifica sin ASS para medir el ruido de píxeles, y el umbral exigido es el máximo entre un mínimo absoluto (0,5 %) y el ruido multiplicado por 3 más 0,2 %. El manifiesto registra `negative_control_changed_ratio` y `required_changed_ratio`.
- Timeouts (60 s para ffprobe y extracción de banda; 600 s para codificaciones FFmpeg), `--prune-work-days N` para limpiar `output/.work`, cache del modelo de alineación por (idioma, device), claves del registro relativas al proyecto (dedup estable al mover la carpeta) y `KeyboardInterrupt` ya no se traga en el bucle principal.
- `validate_video` convierte la duración ausente en `StageValidationError` controlado en lugar de `TypeError`.
- Tests automatizados: `tests/test_logic.py` (lógica pura, sin GPU ni FFmpeg) y `tests/test_integration.py` (MP4 sintético + dobles de IA, verifica publicación atómica, registro v2, control negativo y dedup). 34 tests, ejecutar con `python -m unittest discover -s tests -v`.
- El proyecto se inicializó como repositorio git; `input/` y `output/` quedan fuera del control de versiones por ser binarios/generados.
