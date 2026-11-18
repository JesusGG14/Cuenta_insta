# Cuenta Insta — 10 Reels de Fitness

10 reels verticales (1080×1920, 30 fps) listos para subir a Instagram, sobre los nichos fitness con más interés:

| # | Nicho | Reel |
|---|---|---|
| 1 | Pérdida de grasa | 3 errores que no te dejan perder grasa |
| 2 | Hipertrofia | Cuántas series necesitas para ganar músculo |
| 3 | Nutrición | Cuánta proteína necesitas al día |
| 4 | Entreno en casa | Rutina de 10 minutos sin material |
| 5 | Glúteos | Los 4 mejores ejercicios para glúteos |
| 6 | Abdomen | Mil abdominales no te quitan la barriga |
| 7 | Suplementación | Suplementos que sí funcionan |
| 8 | Cardio | Caminar: el cardio más infravalorado |
| 9 | Movilidad | 5 minutos de movilidad para tu espalda |
| 10 | Recuperación | El anabólico gratis: dormir |

- `output/*.mp4`: los vídeos finales (voz en off, música, efectos, subtítulos animados).
- `output/*_portada.png`: portadas.
- `output/GUIONES.md`: guion completo, textos en pantalla, copy y hashtags de cada reel.

## Cómo editar y volver a generar

Todo el contenido está en `reels/content.py` (textos, colores, voz, iconos, ejercicios).
Pon tu usuario en `HANDLE` para que aparezca en los vídeos.

```bash
pip install kokoro-onnx soundfile pycairo scipy numpy pillow
# modelo de voz (Kokoro, licencia Apache 2.0) en reels/models/
curl -L -o reels/models/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -L -o reels/models/voices-v1.0.bin  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
python3 reels/render.py          # los 10
python3 reels/render.py 03       # solo el 3
python3 reels/gen_docs.py        # regenera GUIONES.md
```

Al cambiar un texto de voz, borra `build/` (caché de audio) para que se vuelva a generar.

## Voz clonada (tu voz)

Los vídeos de `output/` usan tu voz clonada con XTTS-v2 a partir de una muestra de audio.
Para regenerarlos (requiere `coqui-tts`, `torch` CPU y el modelo XTTS-v2 en `reels/models/xtts/`):

```bash
python reels/clone_tts.py ruta/a/tu_voz.m4a        # crea build_clone/
REELS_CACHE=build_clone python3 reels/render.py   # monta los vídeos con tu voz
```
