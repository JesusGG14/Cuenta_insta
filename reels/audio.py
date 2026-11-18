# -*- coding: utf-8 -*-
"""Voz (Kokoro TTS), música de fondo sintetizada y efectos de sonido."""
import os
import numpy as np

SR = 48000
_KOKORO = None


def kokoro():
    global _KOKORO
    if _KOKORO is None:
        from kokoro_onnx import Kokoro
        mdir = os.environ.get("KOKORO_DIR", os.path.join(os.path.dirname(__file__), "models"))
        _KOKORO = Kokoro(os.path.join(mdir, "kokoro-v1.0.onnx"), os.path.join(mdir, "voices-v1.0.bin"))
    return _KOKORO


def resample(x, sr_in, sr_out=SR):
    n = int(round(len(x) * sr_out / sr_in))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def tts(text, voice, speed=1.12):
    s, sr = kokoro().create(text, voice=voice, speed=speed, lang="es")
    s = np.asarray(s, dtype=np.float32)
    # recorta silencios de los extremos
    thr = 0.01 * np.max(np.abs(s))
    idx = np.where(np.abs(s) > thr)[0]
    if len(idx):
        s = s[max(0, idx[0] - 600): idx[-1] + 1200]
    s = resample(s, sr)
    s = s / (np.max(np.abs(s)) + 1e-9) * 0.9
    return s


# ---------------------------------------------------------------- síntesis
def _env(n, a=0.005, r=0.1):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / r)
    return e


def kick(n=int(0.35 * SR)):
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9) * 0.9


def clap(rng, n=int(0.25 * SR)):
    t = np.arange(n) / SR
    no = rng.standard_normal(n)
    no = np.diff(no, prepend=0)  # paso alto simple
    e = np.exp(-t * 18) * (1 + 0.6 * (np.sin(2 * np.pi * 90 * t) > 0) * (t < 0.03))
    return no * e * 0.25


def hat(rng, n=int(0.06 * SR)):
    t = np.arange(n) / SR
    no = np.diff(rng.standard_normal(n), prepend=0)
    no = np.diff(no, prepend=0)
    return no * np.exp(-t * 70) * 0.06


def saw(freq, n, detune=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for d in (-detune, 0, detune) if detune else (0,):
        ph = (t * freq * (1 + d)) % 1.0
        out += 2 * ph - 1
    return out / (3 if detune else 1)


def lowpass(x, a):
    # filtro de un polo (a cerca de 0 = más grave)
    from scipy.signal import lfilter
    return lfilter([a], [1, -(1 - a)], x)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def music(duration, key=57, bpm=118, seed=0):
    """Loop electrónico tipo 'gym': kick 4/4, clap, hats, bajo y pad menor."""
    rng = np.random.default_rng(seed)
    n = int(duration * SR) + SR
    out = np.zeros(n)
    beat = 60.0 / bpm
    bar = 4 * beat
    # progresión i - VI - III - VII (en menor)
    prog = [0, -4, 3, -2]
    k = kick()
    nbars = int(duration / bar) + 2
    for b in range(nbars):
        root = key + prog[b % 4]
        t0 = b * bar
        for s in range(4):
            i = int((t0 + s * beat) * SR)
            if b > 0 or s >= 2:  # entra el kick tras medio compás
                seg = k[: max(0, min(len(k), n - i))]
                out[i: i + len(seg)] += seg
            if s in (1, 3):
                c = clap(rng)
                seg = c[: max(0, min(len(c), n - i))]
                out[i: i + len(seg)] += seg
            for h in (0.5,):
                j = int((t0 + (s + h) * beat) * SR)
                hh = hat(rng)
                seg = hh[: max(0, min(len(hh), n - j))]
                out[j: j + len(seg)] += seg
        # bajo en corcheas
        for e8 in range(8):
            i = int((t0 + e8 * beat / 2) * SR)
            ln = int(beat / 2 * SR * 0.9)
            if i + ln > n:
                break
            f = mtof(root - 24 + (12 if e8 % 4 == 3 else 0))
            v = lowpass(saw(f, ln), 0.08) * _env(ln, 0.003, 0.12) * 0.35
            out[i: i + ln] += v
        # pad
        i = int(t0 * SR)
        ln = int(bar * SR)
        if i + ln <= n:
            chord = [root, root + 3, root + 7, root + 12]
            pad = sum(saw(mtof(m - 12), ln, 0.004) for m in chord) / 4
            pad = lowpass(pad, 0.04)
            tt = np.arange(ln) / SR
            pe = np.minimum(1, tt / 0.15) * np.minimum(1, (bar - tt) / 0.2)
            out[i: i + ln] += pad * pe * 0.18
    out = out[: int(duration * SR)]
    # fade in/out
    fi = int(0.4 * SR)
    fo = int(1.2 * SR)
    out[:fi] *= np.linspace(0, 1, fi)
    out[-fo:] *= np.linspace(1, 0, fo)
    return (out / (np.max(np.abs(out)) + 1e-9)).astype(np.float32)


def whoosh(seed=1, dur=0.45):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    no = rng.standard_normal(n)
    # barrido: filtro paso bajo que se abre y cierra
    from scipy.signal import lfilter
    out = np.zeros(n)
    y = 0.0
    a_curve = 0.02 + 0.35 * np.sin(np.pi * t / dur) ** 2
    for i in range(n):
        y += a_curve[i] * (no[i] - y)
        out[i] = y
    env = np.sin(np.pi * t / dur) ** 1.5
    return (out * env * 0.5).astype(np.float32)


def pop(freq=880, dur=0.12):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 0.8 * np.exp(-t * 40))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * np.exp(-t * 30) * 0.35).astype(np.float32)


def ding(freq=1318.5, dur=0.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2.01 * t)
    return (x * np.exp(-t * 7) * 0.22).astype(np.float32)


def mix_track(duration, voices, events, key, bpm, seed):
    """voices: [(t, array)]  events: [(t, 'whoosh'|'pop'|'ding')]"""
    n = int(duration * SR)
    vtrack = np.zeros(n, np.float32)
    for t, v in voices:
        i = int(t * SR)
        seg = v[: max(0, min(len(v), n - i))]
        vtrack[i: i + len(seg)] += seg
    sfx = np.zeros(n, np.float32)
    cache = {"whoosh": whoosh(seed), "pop": pop(), "ding": ding()}
    for t, kind in events:
        s = cache[kind]
        i = int(t * SR)
        seg = s[: max(0, min(len(s), n - i))]
        sfx[i: i + len(seg)] += seg
    mus = music(duration, key=key, bpm=bpm, seed=seed)
    # ducking: baja la música cuando habla la voz
    env = np.abs(vtrack)
    win = int(0.25 * SR)
    cs = np.concatenate([[0], np.cumsum(env)])
    lo = np.clip(np.arange(n) - win // 2, 0, n)
    hi = np.clip(np.arange(n) + win // 2, 0, n)
    env = (cs[hi] - cs[lo]) / win
    duck = 1.0 - 0.55 * np.clip(env / 0.08, 0, 1)
    out = vtrack * 1.0 + mus * 0.22 * duck + sfx * 0.8
    peak = np.max(np.abs(out)) + 1e-9
    out = out / peak * 0.95
    return out.astype(np.float32)
