# -*- coding: utf-8 -*-
"""Primitivas gráficas: easing, texto, iconos vectoriales y figuras animadas de ejercicios."""
import math
import cairo

W, H = 1080, 1920
FONT_BLACK = "Inter Display Black"
FONT_BOLD = "Inter Display ExtraBold"


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def ease_out_back(x, s=1.70158):
    x = clamp(x)
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def ease_out_elastic(x):
    x = clamp(x)
    if x in (0, 1):
        return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi) / 3) + 1


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


# ------------------------------------------------------------------ texto
def set_font(ctx, size, black=True):
    ctx.select_font_face(FONT_BLACK if black else FONT_BOLD, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)


def text_w(ctx, s):
    return ctx.text_extents(s).x_advance


def wrap(ctx, text, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_w(ctx, t) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_text(ctx, text, size, max_w, max_lines=3, black=True, min_size=40):
    """Devuelve (size, lines) ajustando el tamaño para que quepa."""
    while True:
        set_font(ctx, size, black)
        lines = wrap(ctx, text, max_w)
        if (len(lines) <= max_lines and all(text_w(ctx, l) <= max_w for l in lines)) or size <= min_size:
            return size, lines
        size -= 4


def draw_text(ctx, text, x, y, size, color=(1, 1, 1), alpha=1.0, black=True, align="center",
              stroke=0, stroke_color=(0, 0, 0), shadow=True):
    set_font(ctx, size, black)
    ext = ctx.text_extents(text)
    if align == "center":
        tx = x - ext.x_advance / 2
    elif align == "right":
        tx = x - ext.x_advance
    else:
        tx = x
    ty = y + size * 0.36  # centrado vertical aproximado (altura de mayúsculas)
    if shadow:
        ctx.move_to(tx + 6, ty + 8)
        ctx.text_path(text)
        ctx.set_source_rgba(0, 0, 0, 0.35 * alpha)
        ctx.fill()
    ctx.move_to(tx, ty)
    ctx.text_path(text)
    if stroke:
        ctx.set_source_rgba(*stroke_color, alpha)
        ctx.set_line_width(stroke)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke_preserve()
    ctx.set_source_rgba(*color, alpha)
    ctx.fill()
    return ext.x_advance


def draw_lines(ctx, lines, x, y, size, line_h=1.08, **kw):
    total = (len(lines) - 1) * size * line_h
    for i, l in enumerate(lines):
        draw_text(ctx, l, x, y - total / 2 + i * size * line_h, size, **kw)


def rounded_rect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def pill(ctx, text, cx, cy, size, bg, fg=(0.05, 0.05, 0.08), alpha=1.0, pad=28):
    set_font(ctx, size, True)
    w = text_w(ctx, text) + pad * 2
    h = size * 1.55
    rounded_rect(ctx, cx - w / 2, cy - h / 2, w, h, h / 2)
    ctx.set_source_rgba(*bg, alpha)
    ctx.fill()
    draw_text(ctx, text, cx, cy, size, color=fg, alpha=alpha, shadow=False)
    return w


# ------------------------------------------------------------------ iconos
# Todos se dibujan centrados en (0,0) dentro de una caja de ~200x200 (escala con s)

def _stroke(ctx, color, lw, alpha=1.0):
    ctx.set_source_rgba(*color, alpha)
    ctx.set_line_width(lw)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()


def _fill(ctx, color, alpha=1.0):
    ctx.set_source_rgba(*color, alpha)
    ctx.fill()


def icon(ctx, name, x, y, s, color, accent, t=0.0, alpha=1.0):
    """Dibuja el icono `name` centrado en (x,y). s = escala (1 = 200px)."""
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    W_ = (1, 1, 1)
    lw = 14
    f = ICONS.get(name)
    if f:
        f(ctx, color, accent, t, alpha, lw)
    ctx.restore()


def _i_dumbbell(ctx, c, a, t, al, lw):
    rounded_rect(ctx, -60, -10, 120, 20, 8); _fill(ctx, c, al)
    for sx in (-1, 1):
        rounded_rect(ctx, sx * 62 - 14, -55, 28, 110, 10); _fill(ctx, a, al)
        rounded_rect(ctx, sx * 88 - 11, -38, 22, 76, 9); _fill(ctx, a, al)


def _i_scale(ctx, c, a, t, al, lw):
    rounded_rect(ctx, -90, -90, 180, 180, 40); _fill(ctx, c, al)
    rounded_rect(ctx, -55, -65, 110, 50, 16); _fill(ctx, (0.12, 0.12, 0.16), al)
    ang = -math.pi / 2 + 0.6 * math.sin(t * 3)
    ctx.move_to(0, -25); ctx.line_to(30 * math.cos(ang) * 0.8, -25 + 30 * math.sin(ang) * 0.8)
    _stroke(ctx, a, 8, al)
    for sx in (-1, 1):
        ctx.arc(sx * 45, 50, 16, 0, 2 * math.pi); _fill(ctx, (0.75, 0.75, 0.8), al)


def _i_flame(ctx, c, a, t, al, lw):
    w = 1 + 0.06 * math.sin(t * 9)
    ctx.save(); ctx.scale(w, 2 - w)
    ctx.move_to(0, -100)
    ctx.curve_to(70, -30, 85, 30, 60, 70)
    ctx.curve_to(40, 100, -40, 100, -60, 70)
    ctx.curve_to(-85, 30, -40, -10, -30, -50)
    ctx.curve_to(-10, -20, 0, -40, 0, -100)
    _fill(ctx, a, al)
    ctx.move_to(0, -10)
    ctx.curve_to(40, 30, 40, 80, 0, 90)
    ctx.curve_to(-40, 80, -35, 40, 0, -10)
    _fill(ctx, (1, 0.9, 0.4), al)
    ctx.restore()


def _i_drumstick(ctx, c, a, t, al, lw):
    ctx.save(); ctx.rotate(-0.7)
    ctx.move_to(-20, 20); ctx.line_to(-20, 90); ctx.line_to(20, 90); ctx.line_to(20, 20); ctx.close_path()
    _fill(ctx, (0.95, 0.92, 0.85), al)
    for sx in (-1, 1):
        ctx.arc(sx * 16, 100, 18, 0, 2 * math.pi); _fill(ctx, (0.95, 0.92, 0.85), al)
    ctx.save(); ctx.scale(1, 1.15)
    ctx.arc(0, -30, 70, 0, 2 * math.pi); ctx.restore(); _fill(ctx, (0.85, 0.5, 0.2), al)
    ctx.save(); ctx.scale(1, 1.15)
    ctx.arc(-15, -45, 30, 0, 2 * math.pi); ctx.restore(); _fill(ctx, (0.95, 0.65, 0.3), al)
    ctx.restore()


def _i_egg(ctx, c, a, t, al, lw):
    ctx.save(); ctx.scale(0.8, 1)
    ctx.move_to(0, -90); ctx.curve_to(80, -90, 90, 80, 0, 90); ctx.curve_to(-90, 80, -80, -90, 0, -90)
    ctx.restore(); _fill(ctx, (0.98, 0.95, 0.88), al)
    ctx.arc(5, 20, 34, 0, 2 * math.pi); _fill(ctx, (1, 0.75, 0.15), al)


def _i_cup(ctx, c, a, t, al, lw):
    ctx.move_to(-70, -60); ctx.line_to(-55, 90); ctx.line_to(55, 90); ctx.line_to(70, -60); ctx.close_path()
    _fill(ctx, (0.97, 0.97, 1), al)
    rounded_rect(ctx, -80, -80, 160, 26, 10); _fill(ctx, a, al)
    for i in range(3):
        ctx.arc(-25 + i * 25, -15 + (i % 2) * 20, 8, 0, 2 * math.pi); _fill(ctx, a, al * 0.7)


def _i_shaker(ctx, c, a, t, al, lw):
    rounded_rect(ctx, -55, -50, 110, 145, 18); _fill(ctx, c, al)
    rounded_rect(ctx, -60, -85, 120, 40, 12); _fill(ctx, a, al)
    rounded_rect(ctx, -18, -110, 36, 30, 8); _fill(ctx, a, al)
    lvl = 10 + 10 * math.sin(t * 5)
    rounded_rect(ctx, -45, lvl, 90, 75 - lvl, 12); _fill(ctx, a, al * 0.55)


def _i_jar(ctx, c, a, t, al, lw):
    rounded_rect(ctx, -65, -60, 130, 155, 24); _fill(ctx, c, al)
    rounded_rect(ctx, -70, -95, 140, 42, 12); _fill(ctx, a, al)
    rounded_rect(ctx, -45, -20, 90, 70, 10); _fill(ctx, a, al)
    draw_text(ctx, "C", 0, 15, 50, color=(0.05, 0.05, 0.08), shadow=False, alpha=al)


def _i_coffee(ctx, c, a, t, al, lw):
    rounded_rect(ctx, -70, -30, 115, 110, 20); _fill(ctx, c, al)
    ctx.arc(55, 25, 28, -math.pi / 2, math.pi / 2); _stroke(ctx, c, 16, al)
    for i in range(3):
        ph = t * 3 + i
        ctx.move_to(-40 + i * 30, -50)
        ctx.curve_to(-55 + i * 30 + 10 * math.sin(ph), -75, -25 + i * 30, -85, -40 + i * 30 + 10 * math.sin(ph), -110)
        _stroke(ctx, a, 10, al * 0.8)


def _i_bolt(ctx, c, a, t, al, lw):
    ctx.move_to(20, -100); ctx.line_to(-60, 15); ctx.line_to(-5, 15); ctx.line_to(-25, 100)
    ctx.line_to(60, -20); ctx.line_to(5, -20); ctx.close_path(); _fill(ctx, a, al)


def _i_clock(ctx, c, a, t, al, lw):
    ctx.arc(0, 0, 90, 0, 2 * math.pi); _fill(ctx, c, al)
    ctx.arc(0, 0, 90, 0, 2 * math.pi); _stroke(ctx, a, 14, al)
    for k in range(12):
        an = k * math.pi / 6
        ctx.move_to(70 * math.cos(an), 70 * math.sin(an)); ctx.line_to(78 * math.cos(an), 78 * math.sin(an))
        _stroke(ctx, (0.2, 0.2, 0.25), 6, al)
    am = t * 2.5 - math.pi / 2
    ah = t * 0.4 - math.pi / 2
    ctx.move_to(0, 0); ctx.line_to(60 * math.cos(am), 60 * math.sin(am)); _stroke(ctx, (0.1, 0.1, 0.14), 9, al)
    ctx.move_to(0, 0); ctx.line_to(40 * math.cos(ah), 40 * math.sin(ah)); _stroke(ctx, a, 11, al)


def _i_target(ctx, c, a, t, al, lw):
    for r, col in ((95, a), (70, c), (45, a), (20, c)):
        ctx.arc(0, 0, r, 0, 2 * math.pi); _fill(ctx, col, al)


def _i_cross(ctx, c, a, t, al, lw):
    ctx.arc(0, 0, 90, 0, 2 * math.pi); _fill(ctx, (0.95, 0.2, 0.25), al)
    ctx.move_to(-38, -38); ctx.line_to(38, 38); ctx.move_to(38, -38); ctx.line_to(-38, 38)
    _stroke(ctx, (1, 1, 1), 22, al)


def _i_check(ctx, c, a, t, al, lw):
    ctx.arc(0, 0, 90, 0, 2 * math.pi); _fill(ctx, (0.2, 0.85, 0.45), al)
    ctx.move_to(-42, 2); ctx.line_to(-12, 34); ctx.line_to(45, -30)
    _stroke(ctx, (1, 1, 1), 22, al)


def _i_pill(ctx, c, a, t, al, lw):
    ctx.save(); ctx.rotate(-0.6 + 0.1 * math.sin(t * 2))
    rounded_rect(ctx, -45, -100, 90, 200, 45); _fill(ctx, c, al)
    ctx.new_path()
    ctx.move_to(-45, 0); ctx.line_to(-45, 55); ctx.arc_negative(0, 55, 45, math.pi, 0); ctx.line_to(45, 0); ctx.close_path()
    _fill(ctx, a, al)
    ctx.restore()


def _i_moon(ctx, c, a, t, al, lw):
    ctx.arc(0, 0, 85, 0, 2 * math.pi)
    ctx.arc_negative(38, -28, 70, 2 * math.pi, 0)
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    _fill(ctx, (1, 0.9, 0.55), al)
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    for i, (sx, sy) in enumerate(((70, -70), (95, 20), (40, 70))):
        r = 8 + 4 * math.sin(t * 4 + i * 2)
        ctx.arc(sx, sy, max(2, r), 0, 2 * math.pi); _fill(ctx, (1, 1, 1), al)


def _i_bed(ctx, c, a, t, al, lw):
    rounded_rect(ctx, -100, 0, 200, 50, 10); _fill(ctx, c, al)
    rounded_rect(ctx, -100, -60, 22, 140, 8); _fill(ctx, a, al)
    rounded_rect(ctx, 80, -20, 20, 100, 8); _fill(ctx, a, al)
    rounded_rect(ctx, -72, -35, 50, 32, 12); _fill(ctx, (0.95, 0.95, 1), al)
    rounded_rect(ctx, -15, -25, 110, 28, 12); _fill(ctx, a, al * 0.7)
    for i in range(3):
        k = (t * 0.8 + i / 3) % 1
        draw_text(ctx, "z", 30 + i * 22 + k * 20, -60 - k * 60 - i * 15, 34 + i * 6,
                  color=(1, 1, 1), alpha=al * (1 - k), shadow=False)


def _i_steps(ctx, c, a, t, al, lw):
    for i, (sx, sy, rot) in enumerate(((-40, 40, -0.2), (40, -40, 0.2))):
        k = 0.5 + 0.5 * math.sin(t * 5 + i * math.pi)
        ctx.save(); ctx.translate(sx, sy - 10 * k); ctx.rotate(rot)
        ctx.save(); ctx.scale(0.6, 1); ctx.arc(0, 0, 50, 0, 2 * math.pi); ctx.restore(); _fill(ctx, c, al)
        ctx.save(); ctx.scale(0.6, 0.6); ctx.arc(0, 115, 35, 0, 2 * math.pi); ctx.restore(); _fill(ctx, a, al)
        ctx.restore()


def _i_plate(ctx, c, a, t, al, lw):
    ctx.arc(0, 0, 90, 0, 2 * math.pi); _fill(ctx, (0.97, 0.97, 1), al)
    ctx.arc(0, 0, 66, 0, 2 * math.pi); _fill(ctx, (0.88, 0.88, 0.92), al)
    ctx.arc(-20, -12, 28, 0, 2 * math.pi); _fill(ctx, (0.3, 0.8, 0.35), al)
    ctx.arc(22, -18, 22, 0, 2 * math.pi); _fill(ctx, (0.9, 0.55, 0.2), al)
    ctx.arc(5, 28, 26, 0, 2 * math.pi); _fill(ctx, (0.95, 0.85, 0.6), al)


def _i_phone(ctx, c, a, t, al, lw):
    rounded_rect(ctx, -55, -100, 110, 200, 22); _fill(ctx, c, al)
    rounded_rect(ctx, -44, -80, 88, 150, 8); _fill(ctx, (0.1, 0.1, 0.14), al)
    rounded_rect(ctx, -30, -60, 60, 30, 8); _fill(ctx, a, al)
    rounded_rect(ctx, -30, -20, 45, 20, 6); _fill(ctx, a, al * 0.6)
    ctx.arc(0, 85, 7, 0, 2 * math.pi); _fill(ctx, (0.3, 0.3, 0.35), al)


def _i_stairs(ctx, c, a, t, al, lw):
    ctx.move_to(-90, 90)
    for i in range(4):
        ctx.line_to(-90 + i * 45, 90 - (i + 1) * 45)
        ctx.line_to(-90 + (i + 1) * 45, 90 - (i + 1) * 45)
    ctx.line_to(90, 90); ctx.close_path(); _fill(ctx, c, al)
    k = (t * 0.6) % 1
    i = int(k * 4)
    ctx.arc(-68 + i * 45, 90 - (i + 1) * 45 - 22, 16, 0, 2 * math.pi); _fill(ctx, a, al)


def _i_repeat(ctx, c, a, t, al, lw):
    ctx.save(); ctx.rotate(t * 1.5)
    ctx.arc(0, 0, 70, 0.3, math.pi - 0.3); _stroke(ctx, a, 22, al)
    ctx.arc(0, 0, 70, math.pi + 0.3, 2 * math.pi - 0.3); _stroke(ctx, a, 22, al)
    for ang in (math.pi - 0.3, 2 * math.pi - 0.3):
        x, y = 70 * math.cos(ang), 70 * math.sin(ang)
        ctx.save(); ctx.translate(x, y); ctx.rotate(ang + math.pi / 2)
        ctx.move_to(-28, 0); ctx.line_to(28, 0); ctx.line_to(0, 30); ctx.close_path(); _fill(ctx, a, al)
        ctx.restore()
    ctx.restore()


def _i_calendar(ctx, c, a, t, al, lw):
    rounded_rect(ctx, -90, -75, 180, 165, 20); _fill(ctx, c, al)
    rounded_rect(ctx, -90, -75, 180, 50, 20); _fill(ctx, a, al)
    ctx.rectangle(-90, -40, 180, 15); _fill(ctx, a, al)
    for r in range(3):
        for q in range(4):
            on = (r * 4 + q) in (1, 4, 6, 9)
            rounded_rect(ctx, -70 + q * 37, -10 + r * 33, 26, 24, 5)
            _fill(ctx, a if on else (0.8, 0.8, 0.85), al)


def _i_chair(ctx, c, a, t, al, lw):
    rounded_rect(ctx, -60, -100, 30, 130, 10); _fill(ctx, a, al)
    rounded_rect(ctx, -60, 0, 120, 30, 10); _fill(ctx, c, al)
    ctx.move_to(-48, 30); ctx.line_to(-48, 100); ctx.move_to(48, 30); ctx.line_to(48, 100)
    _stroke(ctx, c, 16, al)


def _i_bookmark(ctx, c, a, t, al, lw):
    ctx.move_to(-55, -90); ctx.line_to(55, -90); ctx.line_to(55, 90); ctx.line_to(0, 50); ctx.line_to(-55, 90)
    ctx.close_path(); _fill(ctx, c, al)


def _i_heart(ctx, c, a, t, al, lw):
    ctx.move_to(0, 85)
    ctx.curve_to(-120, 0, -70, -100, 0, -40)
    ctx.curve_to(70, -100, 120, 0, 0, 85)
    _fill(ctx, (1, 0.25, 0.4), al)


def _i_send(ctx, c, a, t, al, lw):
    ctx.move_to(-85, -10); ctx.line_to(85, -80); ctx.line_to(20, 85); ctx.line_to(0, 10); ctx.close_path()
    _fill(ctx, c, al)


ICONS = {
    "dumbbell": _i_dumbbell, "scale": _i_scale, "flame": _i_flame, "drumstick": _i_drumstick,
    "egg": _i_egg, "cup": _i_cup, "shaker": _i_shaker, "jar": _i_jar, "coffee": _i_coffee,
    "bolt": _i_bolt, "clock": _i_clock, "target": _i_target, "cross": _i_cross, "check": _i_check,
    "pill": _i_pill, "moon": _i_moon, "bed": _i_bed, "steps": _i_steps, "plate": _i_plate,
    "phone": _i_phone, "stairs": _i_stairs, "repeat": _i_repeat, "calendar": _i_calendar,
    "chair": _i_chair, "bookmark": _i_bookmark, "heart": _i_heart, "send": _i_send,
}


# ------------------------------------------------------------------ figuras
# Cinemática directa: ángulos en grados, 0 = arriba, 90 = delante (derecha), 180 = abajo, 270 = atrás.
SEG = {"torso": 55, "thigh": 46, "shin": 46, "uarm": 30, "farm": 28, "neck": 20}
STAND = dict(tor=0, th1=180, sh1=180, th2=180, sh2=180, ua1=180, fa1=180, ua2=180, fa2=180, arch=0, hop=0)


def P(**kw):
    d = dict(STAND)
    d.update(kw)
    return d


EXERCISES = {
    # (pose A, pose B, periodo en s, props)
    "squat": (P(ua1=95, fa1=90, ua2=95, fa2=90, tor=5),
              P(tor=40, th1=100, sh1=200, th2=100, sh2=200, ua1=90, fa1=90, ua2=90, fa2=90), 1.8, []),
    "deadlift": (P(tor=3, ua1=180, fa1=180, ua2=180, fa2=180),
                 P(tor=68, th1=125, sh1=200, th2=125, sh2=200, ua1=178, fa1=178, ua2=178, fa2=178), 2.0, ["barbell"]),
    "rdl": (P(tor=3),
            P(tor=78, th1=163, sh1=182, th2=163, sh2=182, ua1=180, fa1=180, ua2=180, fa2=180), 2.2, ["barbell"]),
    "pushup": (P(tor=67, th1=247, sh1=247, th2=247, sh2=247, ua1=180, fa1=180, ua2=180, fa2=180),
               P(tor=82, th1=262, sh1=262, th2=262, sh2=262, ua1=225, fa1=90, ua2=225, fa2=90), 1.6, []),
    "plank": (P(tor=78, th1=258, sh1=258, th2=258, sh2=258, ua1=180, fa1=90, ua2=180, fa2=90),
              P(tor=79, th1=259, sh1=259, th2=259, sh2=259, ua1=180, fa1=90, ua2=180, fa2=90, arch=-3), 2.4, []),
    "jumping_jack": (P(th1=176, th2=184, ua1=200, fa1=190, ua2=160, fa2=170),
                     P(th1=155, sh1=158, th2=205, sh2=202, ua1=330, fa1=345, ua2=30, fa2=15, hop=14), 0.9, ["front"]),
    "lunge": (P(),
              P(th1=100, sh1=180, th2=200, sh2=250), 2.0, []),
    "hip_thrust": (P(tor=268, th1=45, sh1=160, th2=45, sh2=160, ua1=95, fa1=90, ua2=95, fa2=90),
                   P(tor=245, th1=72, sh1=190, th2=72, sh2=190, ua1=110, fa1=100, ua2=110, fa2=100), 2.0, ["plate_hip"]),
    "bridge": (P(tor=268, th1=45, sh1=160, th2=60, sh2=60, ua1=95, fa1=95, ua2=95, fa2=95),
               P(tor=245, th1=72, sh1=190, th2=65, sh2=65, ua1=110, fa1=100, ua2=110, fa2=100), 2.2, []),
    "bulgarian": (P(th1=172, sh1=180, th2=195, sh2=300, tor=8),
                  P(th1=105, sh1=185, th2=205, sh2=300, tor=22), 2.0, ["bench2"]),
    "walk": (P(th1=160, sh1=170, th2=200, sh2=215, ua1=205, fa1=200, ua2=155, fa2=140),
             P(th1=200, sh1=215, th2=160, sh2=170, ua1=155, fa1=140, ua2=205, fa2=200), 1.1, ["scroll"]),
    "cat_cow": (P(tor=77, th1=180, sh1=270, th2=180, sh2=270, ua1=180, fa1=180, ua2=180, fa2=180, arch=22),
                P(tor=77, th1=180, sh1=270, th2=180, sh2=270, ua1=180, fa1=180, ua2=180, fa2=180, arch=-16), 3.0, []),
    "thoracic": (P(tor=77, th1=180, sh1=270, th2=180, sh2=270, ua1=180, fa1=180, ua2=170, fa2=170),
                 P(tor=77, th1=180, sh1=270, th2=180, sh2=270, ua1=180, fa1=180, ua2=5, fa2=5), 2.6, []),
    "hip_flexor": (P(th1=110, sh1=180, th2=190, sh2=270, ua1=200, fa1=70, ua2=200, fa2=70),
                   P(th1=88, sh1=172, th2=212, sh2=275, ua1=200, fa1=70, ua2=200, fa2=70), 3.0, []),
    "child": (P(tor=112, th1=135, sh1=270, th2=135, sh2=270, ua1=95, fa1=90, ua2=95, fa2=90, arch=8),
              P(tor=116, th1=137, sh1=270, th2=137, sh2=270, ua1=98, fa1=92, ua2=98, fa2=92, arch=14), 3.4, []),
}


def _dir(a):
    r = math.radians(a)
    return math.sin(r), -math.cos(r)


def _add(p, a, l):
    dx, dy = _dir(a)
    return (p[0] + dx * l, p[1] + dy * l)


def solve(pose):
    hip = (0.0, 0.0)
    neck = _add(hip, pose["tor"], SEG["torso"])
    head = _add(neck, pose["tor"] + pose["arch"] * 0.8, SEG["neck"])
    pts = {"hip": hip, "neck": neck, "head": head}
    for i in ("1", "2"):
        k = _add(hip, pose["th" + i], SEG["thigh"])
        pts["k" + i] = k
        pts["f" + i] = _add(k, pose["sh" + i], SEG["shin"])
        e = _add(neck, pose["ua" + i], SEG["uarm"])
        pts["e" + i] = e
        pts["h" + i] = _add(e, pose["fa" + i], SEG["farm"])
    return pts


def pose_at(name, t):
    A, B, period, props = EXERCISES[name]
    if name == "walk":
        ph = (t / period) % 1.0
        k = 0.5 - 0.5 * math.cos(2 * math.pi * ph)
    else:
        k = ease_in_out(0.5 - 0.5 * math.cos(2 * math.pi * t / period))
    pose = {key: lerp(A[key], B[key], k) for key in A}
    return pose, k, props


def draw_figure(ctx, name, t, cx, ground_y, scale, col, col2, accent, alpha=1.0):
    pose, k, props = pose_at(name, t)
    pts = solve(pose)
    front = "front" in props
    ys = [p[1] for kk, p in pts.items() if kk[0] in "fhk"] + [pts["head"][1] + 16, pts["hip"][1]]
    lowest = max(ys)
    xs = [p[0] for p in pts.values()]
    anchor = "hip" if (front or "scroll" in props) else "f1"
    ptsA = solve(EXERCISES[name][0])
    xa = [p[0] for p in ptsA.values()]
    off = (min(xa) + max(xa)) / 2 - ptsA[anchor][0]
    if name in ("lunge", "hip_flexor", "bulgarian"):
        off = 0
        midx = (pts["f1"][0] + pts["f2"][0]) / 2
    else:
        midx = pts[anchor][0] + off
    hop = pose.get("hop", 0) * math.sin(math.pi * k) if front else 0

    def T(p):
        return (cx + (p[0] - midx) * scale, ground_y + (p[1] - lowest - hop) * scale)

    ctx.save()
    # sombra
    ctx.save()
    ctx.translate(cx, ground_y + 8)
    ctx.scale(1, 0.12)
    ctx.arc(0, 0, (max(xs) - min(xs) + 40) * scale * 0.55, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(0, 0, 0, 0.35 * alpha)
    ctx.fill()
    # suelo
    ctx.move_to(cx - 420, ground_y + 6)
    ctx.line_to(cx + 420, ground_y + 6)
    ctx.set_source_rgba(1, 1, 1, 0.18 * alpha)
    ctx.set_line_width(6)
    ctx.stroke()
    if "scroll" in props:
        off = (t * 260) % 120
        for i in range(-4, 5):
            x = cx + i * 120 - off
            ctx.move_to(x, ground_y + 26)
            ctx.line_to(x + 50, ground_y + 26)
        ctx.set_source_rgba(1, 1, 1, 0.25 * alpha)
        ctx.set_line_width(6)
        ctx.stroke()

    lw = 15 * scale
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)

    def limb(a, b, c, color):
        ctx.move_to(*T(pts[a]))
        ctx.line_to(*T(pts[b]))
        ctx.line_to(*T(pts[c]))
        ctx.set_source_rgba(*color, alpha)
        ctx.set_line_width(lw)
        ctx.stroke()

    if "bench2" in props:
        fx, fy = T(pts["f2"])
        bh = ground_y - fy
        rounded_rect(ctx, fx - 70 * scale / 3.2, fy + 8, 160 * scale / 3.2, bh, 10)
        ctx.set_source_rgba(*accent, 0.85 * alpha)
        ctx.fill()

    # extremidades lejanas (color secundario)
    limb("hip", "k2", "f2", col2)
    limb("neck", "e2", "h2", col2)
    # torso (curva con arqueo)
    hx, hy = T(pts["hip"])
    nx, ny = T(pts["neck"])
    mx, my = (hx + nx) / 2, (hy + ny) / 2
    dx, dy = nx - hx, ny - hy
    ln = math.hypot(dx, dy) + 1e-6
    ox, oy = -dy / ln, dx / ln  # normal
    arch = pose.get("arch", 0) * scale
    # la normal debe apuntar "arriba" para que arch>0 redondee la espalda hacia arriba
    if oy > 0:
        ox, oy = -ox, -oy
    ctx.move_to(hx, hy)
    ctx.curve_to(mx + ox * arch, my + oy * arch, mx + ox * arch, my + oy * arch, nx, ny)
    ctx.set_source_rgba(*col, alpha)
    ctx.set_line_width(lw * 1.25)
    ctx.stroke()
    # cabeza
    hx2, hy2 = T(pts["head"])
    ctx.arc(hx2, hy2, 15 * scale, 0, 2 * math.pi)
    ctx.set_source_rgba(*col, alpha)
    ctx.fill()
    # extremidades cercanas
    limb("hip", "k1", "f1", col)
    limb("neck", "e1", "h1", col)

    if "barbell" in props:
        px, py = T(((pts["h1"][0] + pts["h2"][0]) / 2, (pts["h1"][1] + pts["h2"][1]) / 2))
        ctx.arc(px, py, 26 * scale, 0, 2 * math.pi)
        ctx.set_source_rgba(*accent, alpha)
        ctx.fill()
        ctx.arc(px, py, 7 * scale, 0, 2 * math.pi)
        ctx.set_source_rgba(0.1, 0.1, 0.12, alpha)
        ctx.fill()
    if "plate_hip" in props:
        px, py = T(pts["hip"])
        py -= 22 * scale
        ctx.arc(px, py, 22 * scale, 0, 2 * math.pi)
        ctx.set_source_rgba(*accent, alpha)
        ctx.fill()
        ctx.arc(px, py, 6 * scale, 0, 2 * math.pi)
        ctx.set_source_rgba(0.1, 0.1, 0.12, alpha)
        ctx.fill()
    ctx.restore()
