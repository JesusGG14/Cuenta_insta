# -*- coding: utf-8 -*-
"""Monta cada reel: voz -> calendario de escenas -> audio -> fotogramas animados -> MP4 1080x1920.

Uso:
    python3 reels/render.py            # renderiza los 10
    python3 reels/render.py 01 05      # solo los que empiecen por esos ids
"""
import math
import os
import subprocess
import sys
import wave

import cairo
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import audio  # noqa: E402
from content import REELS, HANDLE  # noqa: E402
from gfx import (W, H, clamp, ease_out_cubic, ease_out_back, ease_out_elastic, ease_in_out, lerp, mix,  # noqa: E402
                 set_font, text_w, fit_text, draw_text, draw_lines, rounded_rect, pill, icon, draw_figure)

FPS = 30
VOICE_DELAY = 0.30
TAIL = 0.50
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")
CACHE = os.path.join(ROOT, os.environ.get("REELS_CACHE", "build"))
WHITE = (1, 1, 1)
DARK = (0.05, 0.05, 0.08)


def appear(lt, delay, length=0.45, fn=ease_out_back):
    return fn((lt - delay) / length) if lt > delay else 0.0


# ================================================================== planificación
def plan(reel):
    os.makedirs(CACHE, exist_ok=True)
    t = 0.0
    scenes = []
    for i, sc in enumerate(reel["scenes"]):
        cf = os.path.join(CACHE, f"{reel['id']}_{i}.npy")
        if os.path.exists(cf):
            v = np.load(cf)
        else:
            v = audio.tts(sc["voice"], reel["voice"])
            np.save(cf, v)
        vd = len(v) / audio.SR
        dur = VOICE_DELAY + vd + TAIL + (1.3 if sc["type"] == "cta" else 0)
        scenes.append({"sc": sc, "start": t, "dur": dur, "voice": v, "vdur": vd,
                       "subs": subtitle_chunks(sc["voice"], vd)})
        t += dur
    return scenes, t


def subtitle_chunks(text, vdur):
    words = text.replace("—", " ").split()
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        joined = " ".join(cur)
        if len(cur) >= 3 or len(joined) > 16 or w[-1] in ".,:;?!":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    # peso por palabra: letras + pausa en signos de puntuación
    def weight(w):
        return len(w) + 2 + (6 if w[-1] in ".:;?!" else 3 if w[-1] == "," else 0)
    total = sum(weight(w) for c in chunks for w in c)
    out, acc = [], 0.0
    for c in chunks:
        ws = []
        for w in c:
            a = acc / total * vdur
            acc += weight(w)
            ws.append((w, a, acc / total * vdur))
        out.append(ws)
    return out


def item_times(s):
    sc = s["sc"]
    n = len(sc.get("items", []))
    if not n:
        return []
    span = s["vdur"]
    return [VOICE_DELAY + 0.15 + i * span / n for i in range(n)]


def sfx_events(scenes):
    ev = []
    for i, s in enumerate(scenes):
        st = s["start"]
        sc = s["sc"]
        if i > 0:
            ev.append((max(0, st - 0.18), "whoosh"))
        if sc.get("num"):
            ev.append((st + 0.25, "pop"))
        for it in item_times(s):
            ev.append((st + it, "pop"))
        if sc["type"] == "stat":
            ev.append((st + 1.5, "ding"))
        if sc["type"] == "cta":
            ev.append((st + 0.5, "ding"))
    return ev


# ================================================================== dibujo
class Theme:
    def __init__(self, reel):
        self.a = reel["accent"]
        self.b = reel["accent2"]
        self.niche = reel["niche"]


def draw_background(ctx, t, th):
    base1 = (0.035, 0.035, 0.06)
    base2 = mix(base1, th.a, 0.16)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *base1)
    g.add_color_stop_rgb(1, *base2)
    ctx.set_source(g)
    ctx.paint()
    # manchas de luz que se mueven
    for k, (col, r, sx, sy, ph) in enumerate(((th.a, 620, 0.25, 0.3, 0.0), (th.b, 520, 0.8, 0.65, 2.0),
                                               (th.a, 460, 0.6, 0.95, 4.0))):
        x = W * sx + 140 * math.sin(t * 0.35 + ph)
        y = H * sy + 180 * math.cos(t * 0.28 + ph * 1.3)
        rg = cairo.RadialGradient(x, y, 0, x, y, r)
        rg.add_color_stop_rgba(0, *col, 0.20)
        rg.add_color_stop_rgba(1, *col, 0.0)
        ctx.set_source(rg)
        ctx.paint()
    # líneas diagonales sutiles
    ctx.save()
    off = (t * 40) % 90
    ctx.set_source_rgba(1, 1, 1, 0.025)
    ctx.set_line_width(18)
    for i in range(-30, 30):
        x = i * 90 + off
        ctx.move_to(x, 0)
        ctx.line_to(x + H * 0.45, H)
    ctx.stroke()
    ctx.restore()
    # viñeta
    vg = cairo.RadialGradient(W / 2, H / 2, H * 0.3, W / 2, H / 2, H * 0.75)
    vg.add_color_stop_rgba(0, 0, 0, 0, 0)
    vg.add_color_stop_rgba(1, 0, 0, 0, 0.55)
    ctx.set_source(vg)
    ctx.paint()


def draw_chrome(ctx, t, total, th):
    # barra de progreso
    ctx.rectangle(0, 0, W, 10)
    ctx.set_source_rgba(1, 1, 1, 0.12)
    ctx.fill()
    g = cairo.LinearGradient(0, 0, W, 0)
    g.add_color_stop_rgb(0, *th.a)
    g.add_color_stop_rgb(1, *th.b)
    ctx.rectangle(0, 0, W * t / total, 10)
    ctx.set_source(g)
    ctx.fill()
    # etiqueta del nicho
    set_font(ctx, 34, True)
    w = text_w(ctx, th.niche) + 60
    rounded_rect(ctx, W / 2 - w / 2, 150, w, 58, 29)
    ctx.set_source_rgba(1, 1, 1, 0.10)
    ctx.fill()
    ctx.arc(W / 2 - w / 2 + 30, 179, 7, 0, 2 * math.pi)
    ctx.set_source_rgba(*th.a, 0.6 + 0.4 * math.sin(t * 6))
    ctx.fill()
    draw_text(ctx, th.niche, W / 2 + 8, 179, 34, color=(1, 1, 1), alpha=0.9, shadow=False)
    if HANDLE:
        draw_text(ctx, HANDLE, W / 2, 1640, 36, color=(1, 1, 1), alpha=0.45, black=False, shadow=False)


def draw_subs(ctx, s, lt, th):
    vt = lt - VOICE_DELAY
    if vt < 0:
        return
    chunk = None
    for c in s["subs"]:
        if c[0][1] <= vt:
            chunk = c
    if chunk is None:
        return
    if vt > chunk[-1][2] + 0.6:
        return
    size = 64
    set_font(ctx, size, True)
    words = [w.upper() for w, _, _ in chunk]
    space = text_w(ctx, " ")
    widths = [text_w(ctx, w) for w in words]
    space = space + 18
    total = sum(widths) + space * (len(words) - 1)
    scale_all = min(1.0, 980 / total)
    x = W / 2 - total * scale_all / 2
    y = 1430
    pop_in = ease_out_back((vt - chunk[0][1]) / 0.18)
    ctx.save()
    ctx.translate(W / 2, y)
    sc0 = (0.85 + 0.15 * pop_in) * scale_all
    ctx.scale(sc0, sc0)
    ctx.translate(-W / 2, -y)
    x = W / 2 - total / 2
    for (w, a, b), ww, wd in zip(chunk, words, widths):
        active = a <= vt < b + 0.05
        col = th.b if active else WHITE
        if active:
            ctx.save()
            k = 1.0 + 0.06 * ease_out_back((vt - a) / 0.15)
            ctx.translate(x + wd / 2, y)
            ctx.scale(k, k)
            ctx.translate(-(x + wd / 2), -y)
        draw_text(ctx, ww, x, y, size, color=col, align="left", stroke=14, shadow=True)
        if active:
            ctx.restore()
        x += wd + space
    ctx.restore()


def num_badge(ctx, text, x, y, r, lt, th, delay=0.1):
    k = appear(lt, delay, 0.5, ease_out_elastic)
    if k <= 0:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(k, k)
    ctx.rotate((1 - k) * -0.6)
    ctx.arc(0, 0, r + 10, 0, 2 * math.pi)
    ctx.set_source_rgba(*th.a, 0.3)
    ctx.fill()
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    g = cairo.LinearGradient(-r, -r, r, r)
    g.add_color_stop_rgb(0, *th.b)
    g.add_color_stop_rgb(1, *th.a)
    ctx.set_source(g)
    ctx.fill()
    fs = r * (1.05 if len(text) == 1 else 0.75)
    draw_text(ctx, text, 0, 0, fs, color=DARK, shadow=False)
    ctx.restore()


def title_block(ctx, title, sub, y, lt, th, size=100, delay=0.25, sub_gap=None):
    k = appear(lt, delay, 0.5, ease_out_cubic)
    if k > 0:
        fs, lines = fit_text(ctx, title, size, 960, 2)
        draw_lines(ctx, lines, W / 2, y + (1 - k) * 60, fs, color=WHITE, alpha=k, stroke=0)
        h = (len(lines) - 1) * fs * 1.08
    else:
        fs, h = size, 0
    if sub:
        k2 = appear(lt, delay + 0.25, 0.5, ease_out_cubic)
        if k2 > 0:
            sy = y + h / 2 + (sub_gap or fs * 0.95)
            sfs, sl = fit_text(ctx, sub, 50, 960, 1, black=False)
            draw_text(ctx, sl[0], W / 2, sy + (1 - k2) * 40, sfs, color=th.b, alpha=k2, black=False)


def scene_hook(ctx, s, lt, th):
    sc = s["sc"]
    k = appear(lt, 0.05, 0.4)
    if sc.get("pill") and k > 0:
        ctx.save()
        ctx.translate(W / 2, 400)
        ctx.scale(k, k)
        pill(ctx, sc["pill"], 0, 0, 46, th.a)
        ctx.restore()
    ki = appear(lt, 0.15, 0.7, ease_out_elastic)
    if ki > 0:
        wob = 0.08 * math.sin(lt * 4)
        ctx.save()
        ctx.translate(W / 2, 720)
        ctx.rotate(wob)
        # halo
        rg = cairo.RadialGradient(0, 0, 0, 0, 0, 330)
        rg.add_color_stop_rgba(0, *th.a, 0.45 * ki)
        rg.add_color_stop_rgba(1, *th.a, 0)
        ctx.set_source(rg)
        ctx.paint()
        ctx.restore()
        icon(ctx, sc["icon"], W / 2, 720 + 12 * math.sin(lt * 3), 1.55 * ki, WHITE, th.a, lt)
    fs, lines = fit_text(ctx, sc["big"], 118, 960, 3)
    total = (len(lines) - 1) * fs * 1.08
    for i, l in enumerate(lines):
        kl = appear(lt, 0.3 + i * 0.12, 0.45)
        if kl <= 0:
            continue
        y = 1080 - total / 2 + i * fs * 1.08
        shake = (math.sin(lt * 60) * 6 * max(0, 1 - lt / 0.6)) if i == 0 else 0
        col = th.b if i == len(lines) - 1 and len(lines) > 1 else WHITE
        ctx.save()
        ctx.translate(W / 2 + shake, y)
        ctx.scale(kl, kl)
        draw_text(ctx, l, 0, 0, fs, color=col, stroke=0)
        ctx.restore()


def visual(ctx, sc, lt, th, cy=720, scale=1.6, ground=1000, fscale=2.9):
    if sc.get("fig"):
        k = appear(lt, 0.1, 0.5, ease_out_cubic)
        draw_figure(ctx, sc["fig"], lt, W / 2, ground, fscale, WHITE, mix(th.a, (0.2, 0.2, 0.25), 0.25), th.b, alpha=k)
    elif sc.get("icon"):
        k = appear(lt, 0.15, 0.6, ease_out_elastic)
        if k > 0:
            rg = cairo.RadialGradient(W / 2, cy, 0, W / 2, cy, 300)
            rg.add_color_stop_rgba(0, *th.a, 0.35 * k)
            rg.add_color_stop_rgba(1, *th.a, 0)
            ctx.set_source(rg)
            ctx.paint()
            icon(ctx, sc["icon"], W / 2, cy + 10 * math.sin(lt * 3), scale * k, WHITE, th.a, lt)
    if sc.get("mark") == "x":
        k = appear(lt, 1.0, 0.4, ease_out_back)
        if k > 0:
            icon(ctx, "cross", W / 2 + 150, cy + 120, 0.75 * k, WHITE, th.a, lt)


def scene_point(ctx, s, lt, th):
    sc = s["sc"]
    if sc.get("num"):
        num_badge(ctx, sc["num"], W / 2, 330, 64, lt, th)
    visual(ctx, sc, lt, th, cy=690, scale=1.6, ground=1000, fscale=2.8)
    title_block(ctx, sc["title"], sc.get("sub"), 1120, lt, th, size=100)


def scene_figure(ctx, s, lt, th):
    sc = s["sc"]
    title_block(ctx, sc["title"], sc.get("sub"), 340, lt, th, size=104, delay=0.05)
    k = appear(lt, 0.15, 0.5, ease_out_cubic)
    # plataforma luminosa
    rg = cairo.RadialGradient(W / 2, 1180, 0, W / 2, 1180, 460)
    rg.add_color_stop_rgba(0, *th.a, 0.35 * k)
    rg.add_color_stop_rgba(1, *th.a, 0)
    ctx.set_source(rg)
    ctx.paint()
    draw_figure(ctx, sc["fig"], lt, W / 2, 1210, 3.3, WHITE, mix(th.a, (0.2, 0.2, 0.25), 0.25), th.b, alpha=k)
    if sc.get("num"):
        num_badge(ctx, sc["num"], 150, 600, 58, lt, th, delay=0.2)
    if sc.get("secs"):
        kr = appear(lt, 0.3, 0.5)
        if kr > 0:
            cx, cy, r = 930, 600, 72
            ctx.save()
            ctx.translate(cx, cy)
            ctx.scale(kr, kr)
            ctx.arc(0, 0, r, 0, 2 * math.pi)
            ctx.set_source_rgba(0, 0, 0, 0.35)
            ctx.fill()
            ctx.arc(0, 0, r, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, 0.15)
            ctx.set_line_width(12)
            ctx.stroke()
            p = clamp((lt - 0.3) / max(0.1, s["dur"] - 0.5))
            ctx.arc(0, 0, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * p)
            ctx.set_source_rgb(*th.b)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()
            draw_text(ctx, f"{sc['secs']}s", 0, 0, 46, color=WHITE, shadow=False)
            ctx.restore()


def scene_stat(ctx, s, lt, th):
    sc = s["sc"]
    if sc.get("num"):
        num_badge(ctx, sc["num"], W / 2, 330, 60, lt, th)
    visual(ctx, {"icon": sc.get("icon")}, lt, th, cy=560, scale=1.0)
    k = appear(lt, 0.3, 0.5)
    if k > 0:
        val = sc["value"]
        if sc.get("count"):
            target = int(val)
            p = ease_out_cubic((lt - 0.3) / 1.2)
            cur = int(round(target * p))
            val = f"{cur:,}".replace(",", ".")
            if p >= 1:
                val = f"{target:,}".replace(",", ".")
        fs, lines = fit_text(ctx, sc["value"] if not sc.get("count") else val, 210, 960, 1)
        ctx.save()
        ctx.translate(W / 2, 840)
        ctx.scale(k, k)
        # brillo
        draw_text(ctx, val, 0, 0, fs, color=th.a, stroke=0)
        ctx.restore()
        ku = appear(lt, 0.6, 0.4)
        if ku > 0:
            draw_text(ctx, sc.get("unit", ""), W / 2, 990 + (1 - ku) * 30, 72, color=WHITE, alpha=ku)
    title_block(ctx, sc["title"], sc.get("sub"), 1140, lt, th, size=88, delay=0.7, sub_gap=80)


def scene_bars(ctx, s, lt, th):
    sc = s["sc"]
    k = appear(lt, 0.05, 0.4, ease_out_cubic)
    fs, lines = fit_text(ctx, sc["title"], 76, 960, 2)
    draw_lines(ctx, lines, W / 2, 360 + (1 - k) * 40, fs, color=WHITE, alpha=k)
    bars = sc["bars"]
    notes = sc.get("notes", [])
    n = len(bars)
    span = max(1.0, s["vdur"] * 0.7)
    row_h = min(250, 760 / n)
    y0 = 560
    for i, (label, val, hi) in enumerate(bars):
        d = VOICE_DELAY + i * span / n
        kb = appear(lt, d, 0.35, ease_out_cubic)
        if kb <= 0:
            continue
        y = y0 + i * row_h
        draw_text(ctx, label, 90, y, 52, color=WHITE, alpha=kb, align="left")
        grow = ease_out_cubic((lt - d) / 0.9)
        bw = 900 * val * grow
        rounded_rect(ctx, 90, y + 50, 900, 70, 35)
        ctx.set_source_rgba(1, 1, 1, 0.08 * kb)
        ctx.fill()
        if bw > 10:
            rounded_rect(ctx, 90, y + 50, max(70, bw), 70, 35)
            if hi:
                g = cairo.LinearGradient(90, 0, 90 + bw, 0)
                g.add_color_stop_rgb(0, *th.a)
                g.add_color_stop_rgb(1, *th.b)
                ctx.set_source(g)
            else:
                ctx.set_source_rgba(0.55, 0.55, 0.62, kb)
            ctx.fill()
        if i < len(notes):
            kn = appear(lt, d + 0.6, 0.4)
            if kn > 0:
                ctx.save()
                tx = 990
                ctx.translate(tx, y)
                ctx.scale(kn, kn)
                draw_text(ctx, notes[i], 0, 0, 52, color=th.b if hi else (0.8, 0.8, 0.85), align="right")
                ctx.restore()


def scene_list(ctx, s, lt, th):
    sc = s["sc"]
    k = appear(lt, 0.05, 0.4, ease_out_cubic)
    fs, lines = fit_text(ctx, sc["title"], 92, 960, 1)
    draw_lines(ctx, lines, W / 2, 380 + (1 - k) * 40, fs, color=th.b if not sc.get("bad") else (1, 0.35, 0.4),
               alpha=k)
    times = item_times(s)
    n = len(sc["items"])
    row_h = 165 if n <= 4 else 140
    y0 = 560
    for i, ((ic, txt, right), ti) in enumerate(zip(sc["items"], times)):
        kk = appear(lt, ti, 0.4, ease_out_cubic)
        if kk <= 0:
            continue
        y = y0 + i * row_h
        x_off = (1 - kk) * -300
        ctx.save()
        ctx.translate(x_off, 0)
        rounded_rect(ctx, 60, y - 62, 960, 124, 30)
        ctx.set_source_rgba(1, 1, 1, 0.09 * kk)
        ctx.fill()
        rounded_rect(ctx, 60, y - 62, 14, 124, 7)
        ctx.set_source_rgba(*th.a, kk)
        ctx.fill()
        icon(ctx, ic, 150, y, 0.42, WHITE, th.a, lt, alpha=kk)
        set_font(ctx, 52, True)
        rw = 0
        if right:
            rw = draw_text(ctx, right, 990, y, 60, color=th.b, alpha=kk, align="right")
        fs2, ls2 = fit_text(ctx, txt, 52, 990 - 220 - rw - 30, 1)
        tw = draw_text(ctx, ls2[0], 220, y, fs2, color=WHITE, alpha=kk, align="left")
        if sc.get("bad"):
            p = ease_out_cubic((lt - ti - 0.35) / 0.35)
            if p > 0:
                ctx.move_to(212, y + 2)
                ctx.line_to(212 + (tw + 16) * p, y + 2)
                ctx.set_source_rgba(1, 0.3, 0.35, kk)
                ctx.set_line_width(10)
                ctx.stroke()
        ctx.restore()
    # contador acumulado para listas con gramos
    if all(r and r.endswith("g") for _, _, r in sc["items"]):
        tot = 0
        for (_, _, r), ti in zip(sc["items"], times):
            if lt >= ti:
                tot += int(r.split()[0])
        kt = appear(lt, times[0], 0.4)
        if kt > 0:
            y = y0 + n * row_h + 30
            draw_text(ctx, f"TOTAL: {tot} g", W / 2, y, 66, color=th.a, alpha=kt)
    if sc.get("foot"):
        kf = appear(lt, times[-1] + 0.5, 0.4)
        if kf > 0:
            draw_text(ctx, sc["foot"], W / 2, y0 + n * row_h + 10, 38, color=(0.8, 0.8, 0.85), alpha=kf, black=False)


def scene_cta(ctx, s, lt, th):
    sc = s["sc"]
    for i, ic in enumerate(("bookmark", "heart", "send")):
        k = appear(lt, 0.1 + i * 0.15, 0.6, ease_out_elastic)
        if k <= 0:
            continue
        x = W / 2 + (i - 1) * 260
        bounce = abs(math.sin(lt * 3 + i * 0.8)) * 30
        ctx.save()
        ctx.translate(x, 700 - bounce)
        ctx.arc(0, 0, 110 * k, 0, 2 * math.pi)
        ctx.set_source_rgba(*(th.a if i != 1 else th.b), 0.25)
        ctx.fill()
        ctx.restore()
        icon(ctx, ic, x, 700 - bounce, 0.75 * k, WHITE, th.a, lt)
    k = appear(lt, 0.4, 0.5)
    if k > 0:
        ctx.save()
        ctx.translate(W / 2, 1000)
        pulse = 1 + 0.03 * math.sin(lt * 6)
        ctx.scale(k * pulse, k * pulse)
        fs, lines = fit_text(ctx, sc["title"], 150, 960, 1)
        draw_text(ctx, lines[0], 0, 0, fs, color=th.a)
        ctx.restore()
    k2 = appear(lt, 0.6, 0.5, ease_out_cubic)
    if k2 > 0:
        draw_text(ctx, sc["sub"], W / 2, 1130 + (1 - k2) * 40, 58, color=WHITE, alpha=k2)


DRAW = {"hook": scene_hook, "point": scene_point, "figure": scene_figure, "stat": scene_stat,
        "bars": scene_bars, "list": scene_list, "cta": scene_cta}


def draw_frame(ctx, t, scenes, total, th):
    draw_background(ctx, t, th)
    s = scenes[-1]
    for cand in scenes:
        if cand["start"] <= t < cand["start"] + cand["dur"]:
            s = cand
            break
    lt = t - s["start"]
    # entrada con "punch" de cámara y salida con fundido
    punch = 1 + 0.06 * (1 - ease_out_cubic(lt / 0.35))
    out_k = clamp((s["dur"] - lt) / 0.2) if s is not scenes[-1] else clamp((total - t) / 0.5)
    ctx.push_group()
    ctx.save()
    ctx.translate(W / 2, H / 2)
    ctx.scale(punch, punch)
    ctx.translate(-W / 2, -H / 2)
    DRAW[s["sc"]["type"]](ctx, s, lt, th)
    ctx.restore()
    draw_subs(ctx, s, lt, th)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(out_k)
    # destello en el cambio de escena
    flash = 0.18 * (1 - clamp(lt / 0.15))
    if flash > 0 and s is not scenes[0]:
        ctx.set_source_rgba(1, 1, 1, flash)
        ctx.paint()
    draw_chrome(ctx, t, total, th)


# ================================================================== salida
def write_wav(path, x):
    x16 = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    stereo = np.repeat(x16[:, None], 2, axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(audio.SR)
        w.writeframes(stereo.tobytes())


def render(reel, preview=False):
    th = Theme(reel)
    scenes, total = plan(reel)
    seed = int(reel["id"][:2])
    voices = [(s["start"] + VOICE_DELAY, s["voice"]) for s in scenes]
    mixd = audio.mix_track(total, voices, sfx_events(scenes), reel["key"], 116 + seed % 4 * 2, seed)
    os.makedirs(OUT, exist_ok=True)
    wav = os.path.join(CACHE, reel["id"] + ".wav")
    write_wav(wav, mixd)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    # portada
    draw_frame(ctx, min(1.6, scenes[0]["dur"] - 0.3), scenes, total, th)
    surf.write_to_png(os.path.join(OUT, reel["id"] + "_portada.png"))
    if preview:
        return scenes, total
    mp4 = os.path.join(OUT, reel["id"] + ".mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "21",
           "-pix_fmt", "yuv420p", "-threads", "2", "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-movflags", "+faststart", mp4]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(math.ceil(total * FPS))
    for f in range(nf):
        t = f / FPS
        draw_frame(ctx, t, scenes, total, th)
        surf.flush()
        p.stdin.write(surf.get_data())
    p.stdin.close()
    p.wait()
    print(f"{reel['id']}: {total:.1f}s -> {mp4}", flush=True)
    return scenes, total


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    preview = "--preview" in sys.argv
    for r in REELS:
        if not args or any(r["id"].startswith(a) for a in args):
            render(r, preview=preview)
