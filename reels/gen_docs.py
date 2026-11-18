# -*- coding: utf-8 -*-
"""Genera output/GUIONES.md con guion, textos en pantalla, copy y hashtags de cada reel."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from content import REELS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = ["# 10 Reels de Fitness — Guiones, copys y hashtags\n",
     "Formato: vertical 1080×1920, 30 fps, voz en off en español + música + efectos + subtítulos animados.\n",
     "| # | Nicho | Reel | Vídeo |", "|---|---|---|---|"]
for i, r in enumerate(REELS, 1):
    L.append(f"| {i} | {r['niche'].title()} | {r['title']} | `{r['id']}.mp4` |")
for i, r in enumerate(REELS, 1):
    L += ["", "---", "", f"## {i}. {r['title']}", "",
          f"**Nicho:** {r['niche'].title()} · **Voz:** {'masculina (Álvaro)' if r['voice'].startswith('em') else 'femenina (Dora)'} · "
          f"**Archivo:** `output/{r['id']}.mp4` · **Portada:** `output/{r['id']}_portada.png`", "",
          "| Escena | Texto en pantalla | Voz en off |", "|---|---|---|"]
    for j, s in enumerate(r["scenes"], 1):
        if s["type"] == "hook":
            scr = f"{s.get('pill','')} · **{s['big']}**"
        elif s["type"] in ("list",):
            scr = f"**{s['title']}** — " + " / ".join(f"{t} {v}".strip() for _, t, v in s["items"])
        elif s["type"] == "bars":
            scr = f"**{s['title']}** — " + " / ".join(b[0] for b in s["bars"])
        elif s["type"] == "stat":
            scr = f"**{s['value']} {s.get('unit','')}** · {s['title']} · {s.get('sub','')}"
        else:
            scr = f"**{s['title']}** · {s.get('sub','')}"
        tag = {"hook": "Gancho", "cta": "Cierre (CTA)"}.get(s["type"], f"{j}")
        L.append(f"| {tag} | {scr} | {s['voice']} |")
    L += ["", "**Copy para la publicación:**", "", f"> {r['caption']}", ">", f"> {r['hashtags']}"]
L += ["", "---", "", "## Consejos de publicación", "",
      "- Publica 3–5 reels por semana; mejor franja en España: 13:00–15:00 y 19:30–22:00.",
      "- Usa la portada `_portada.png` como miniatura para que el perfil quede uniforme.",
      "- Al subir, añade un audio en tendencia de Instagram a volumen muy bajo (1–5 %) si quieres impulso extra; la voz ya va mezclada.",
      "- Responde a los comentarios en la primera hora: el reel de proteína invita a comentar el peso.",
      "- Los datos son orientativos y generales; no sustituyen el consejo de un profesional sanitario."]
open(os.path.join(ROOT, "output", "GUIONES.md"), "w").write("\n".join(L) + "\n")
print("ok")
