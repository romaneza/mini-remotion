"""Mix audio: gabung VO + BGM (auto-duck) + SFX pada timestamp tertentu."""
import json
import numpy as np
import wave
from .audiosynth import sfx as synth_sfx, bgm as synth_bgm, SR

def _load_wav(path: str) -> np.ndarray:
    """Baca audio apa pun via ffmpeg jadi float stereo 44.1kHz [-1,1]."""
    import subprocess
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-acodec", "pcm_f32le",
           "-ac", "2", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    return audio

def _rms_envelope(audio: np.ndarray, win_sec: float = 0.1) -> np.ndarray:
    win = int(win_sec * SR)
    if len(audio) < win:
        return np.array([np.sqrt(np.mean(audio ** 2)) if len(audio) else 0.0])
    n_frames = len(audio) // win
    frames = audio[:n_frames * win].reshape(n_frames, win, 2)
    return np.sqrt(np.mean(frames ** 2, axis=(1, 2)))

def auto_duck(bgm_audio: np.ndarray, vo_audio: np.ndarray,
              duck_level: float = 0.25, floor: float = 0.45) -> np.ndarray:
    """Turunkan volume BGM saat VO aktif (sidechain sederhana berbasis envelope RMS)."""
    n = len(bgm_audio)
    env = _rms_envelope(vo_audio)
    if len(env) == 0:
        return bgm_audio
    # threshold adaptif: pakai persentil tinggi dari frame AKTIF saja.
    # Frame hening (RMS ~ 0) tidak boleh menaikkan threshold.
    active = env[env > 1e-4]
    if len(active) < 3:
        return bgm_audio  # VO praktis kosong, tidak perlu duck
    threshold = np.percentile(active, 40) * 0.5  # level "bicara" = 50% dari tipikal
    speaking = (env > threshold).astype(float)
    # smoothing 200ms
    win = max(1, int(0.2 * SR / (0.1 * SR)))
    kernel = np.ones(win) / win
    speaking = np.convolve(speaking, kernel, mode="same")
    # gain per frame: speaking -> duck_level, silence -> 1.0
    gain = (1.0 - speaking) * 1.0 + speaking * duck_level
    # upsample gain ke sample-level
    idx = np.linspace(0, len(gain) - 1, n)
    gain_full = np.interp(idx, np.arange(len(gain)), gain)
    return bgm_audio * gain_full[:, None]

def parse_sfx_spec(spec: str) -> list[dict]:
    """Parse "whoosh@0.5,click@3.2,volume=0.8" -> list {name, time, volume, pan}."""
    items = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        entry = {"volume": 0.8, "pan": 0.0, "kwargs": {}}
        tokens = part.split(":")
        head = tokens[0]
        extra = tokens[1:]
        if "@" in head:
            name, t = head.split("@", 1)
            entry["name"], entry["time"] = name.strip(), float(t)
        else:
            raise ValueError(f"Format SFX '{part}' salah. Pakai: nama@detik")
        for tok in extra:
            k, v = tok.split("=", 1)
            entry[k.strip()] = float(v) if k.strip() != "kwargs" else v
        items.append(entry)
    return items

def mix(vo_path: str | None, bgm_mood: str | None, bgm_volume: float,
        sfx_spec: str | None, duration: float, out_path: str) -> str:
    """Rakit audio final: VO + BGM ducked + SFX, simpan WAV 16-bit stereo."""
    n = int(duration * SR)
    vo = _load_wav(vo_path) if vo_path else None
    if len(vo) < n:
        vo = np.pad(vo, ((0, n - len(vo)), (0, 0)))
    else:
        vo = vo[:n]
    vo_level = np.max(np.abs(vo)) if len(vo) else 0
    if vo_level > 1e-9:
        vo = vo / vo_level * 0.92  # normalisasi VO

    tracks = []
    if vo is not None:
        tracks.append(vo)

    if bgm_mood:
        bgm = synth_bgm(duration, mood=bgm_mood, volume=1.0)
        if vo is not None:
            bgm = auto_duck(bgm, vo)
        bgm *= bgm_volume
        tracks.append(bgm)

    if sfx_spec:
        for item in parse_sfx_spec(sfx_spec):
            clip = synth_sfx(item["name"], **item.get("kwargs", {}))
            clip = clip * item.get("volume", 0.8)
            start = int(item["time"] * SR)
            if start >= n:
                continue
            end = min(n, start + len(clip))
            pad = np.zeros((n, 2))
            pad[start:end] = clip[:end - start]
            tracks.append(pad)

    if not tracks:
        raise ValueError("Tidak ada track audio untuk di-mix.")
    mixed = sum(tracks)
    peak = np.max(np.abs(mixed))
    if peak > 1.0:
        mixed /= peak  # limiter sederhana
    # tulis wav 16-bit
    import wave
    pcm = (np.clip(mixed, -1, 1) * 32767).astype(np.int16)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_path
