# -*- coding: utf-8 -*-
"""Genera todas las locuciones de los reels con TU voz clonada (XTTS-v2).

Uso (en un entorno con coqui-tts + torch):
    python reels/clone_tts.py ruta/a/tu_audio.m4a [ids...]
Después:
    REELS_CACHE=build_clone python3 reels/render.py

Escribe build_clone/<id>_<escena>.npy (48 kHz), que render.py usa como caché de voz.
"""
import os
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from content import REELS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, os.environ.get("REELS_CACHE", "build_clone"))
MODEL_DIR = os.environ.get("XTTS_DIR", os.path.join(os.path.dirname(__file__), "models", "xtts"))
SR = 48000


def prepare_reference(src):
    """Convierte la muestra a WAV mono 22.05 kHz, limpia ruido grave y normaliza."""
    dst = os.path.join(tempfile.gettempdir(), "voz_referencia.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", "22050",
                    "-af", "highpass=f=70,afftdn=nf=-25,loudnorm=I=-18:TP=-2", dst], check=True)
    return dst


def resample(x, sr_in):
    n = int(round(len(x) * SR / sr_in))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def main():
    import torch
    from TTS.tts.configs.xtts_config import XttsConfig
    import soundfile as sf
    import torchaudio
    import TTS.tts.models.xtts as xtts_mod
    from TTS.tts.models.xtts import Xtts

    def _load_audio(path, sampling_rate):  # evita torchcodec: carga con soundfile
        data, sr = sf.read(path, dtype="float32", always_2d=True)
        audio = torch.from_numpy(data.mean(axis=1))[None, :]
        if sr != sampling_rate:
            audio = torchaudio.functional.resample(audio, sr, sampling_rate)
        return audio.clamp(-1, 1)

    xtts_mod.load_audio = _load_audio

    ref = prepare_reference(sys.argv[1])
    ids = sys.argv[2:]
    torch.set_num_threads(os.cpu_count() or 4)
    cfg = XttsConfig()
    cfg.load_json(os.path.join(MODEL_DIR, "config.json"))
    model = Xtts.init_from_config(cfg)
    model.load_checkpoint(cfg, checkpoint_dir=MODEL_DIR, use_deepspeed=False)
    model.eval()
    lat, spk = model.get_conditioning_latents(audio_path=[ref], gpt_cond_len=30, max_ref_length=60)
    os.makedirs(OUT, exist_ok=True)
    for reel in REELS:
        if ids and not any(reel["id"].startswith(i) for i in ids):
            continue
        for i, sc in enumerate(reel["scenes"]):
            path = os.path.join(OUT, f"{reel['id']}_{i}.npy")
            if os.path.exists(path):
                continue
            out = model.inference(sc["voice"], "es", lat, spk, temperature=0.65, speed=1.08,
                                  repetition_penalty=5.0, enable_text_splitting=True)
            w = np.asarray(out["wav"], dtype=np.float32)
            thr = 0.02 * np.max(np.abs(w))
            idx = np.where(np.abs(w) > thr)[0]
            if len(idx):
                w = w[max(0, idx[0] - 400): idx[-1] + 2000]
            w = resample(w, 24000)
            w = w / (np.max(np.abs(w)) + 1e-9) * 0.9
            np.save(path, w)
            print(f"{reel['id']} escena {i}: {len(w) / SR:.1f}s", flush=True)


if __name__ == "__main__":
    main()
