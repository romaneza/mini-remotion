"""Sintesis audio: SFX & musik latar dari nol (NumPy + SciPy), tanpa aset eksternal."""
import numpy as np
from scipy import signal

SR = 44100  # sample rate

def _env(n: int, attack: float, decay: float) -> np.ndarray:
    """Envelope attack-decay linear dalam detik."""
    a = max(1, int(attack * SR))
    d = max(1, int(decay * SR))
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a)
    decay_len = min(d, n - a) if n > a else n
    if decay_len > 0:
        env[a:a + decay_len] = np.linspace(1, 0, decay_len)
    return env

def _pan(stereo: np.ndarray, pan: float) -> np.ndarray:
    """pan -1 (kiri) .. +1 (kanan)."""
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    return stereo * np.array([l, r])[None, :]

def whoosh(dur: float = 0.6, pan: float = 0.0) -> np.ndarray:
    """Whoosh: noise bandpass dengan frekuensi tengah menyapu naik."""
    n = int(dur * SR)
    noise = np.random.default_rng(42).standard_normal(n)
    t = np.linspace(0, dur, n)
    # sweep f-tengah 300Hz -> 2500Hz
    sweep = 300 + (2500 - 300) * (t / dur) ** 2
    fs = 2.0
    q = 1.2
    out = np.empty(n)
    for i in range(n):
        # lfilter dinamis mahal; pendekatan: modulasi amplitude + filtet statis bertahap
        pass
    # praktis: bagi jadi 8 segmen bandpass dengan fc naik, crossfade
    seg = n // 8
    out = np.zeros(n)
    for k in range(8):
        s0, s1 = k * seg, min(n, (k + 1) * seg + int(0.02 * SR))
        b, a = signal.butter(4, [sweep[min(s0, n-1)] / (SR/2), min(0.95, sweep[min(s1, n-1)] * 1.5 / (SR/2))], btype="band")
        chunk = signal.lfilter(b, a, noise[s0:s1])
        fade = np.hanning(len(chunk))
        out[s0:s1] += chunk * fade[:len(chunk)]
    out *= _env(n, 0.15, dur - 0.15)
    out /= max(1e-9, np.max(np.abs(out)))
    stereo = np.stack([out, out], axis=1)
    return _pan(stereo, pan)

def shutter(dur: float = 0.25) -> np.ndarray:
    """Klik kamera: 3 impulse pendek berturutan."""
    n = int(dur * SR)
    out = np.zeros(n)
    for i, off in enumerate([0.0, 0.06, 0.13]):
        idx = int(off * SR)
        ln = int(0.012 * SR)
        click = np.random.default_rng(i).standard_normal(ln) * np.exp(-np.linspace(0, 6, ln))
        out[idx:idx+ln] += click
    out /= max(1e-9, np.max(np.abs(out)))
    return np.stack([out, out], axis=1)

def click(dur: float = 0.08, freq: float = 1800.0) -> np.ndarray:
    """Pop/tick pendek: sine frekuensi tinggi dengan decay instan."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.sin(2 * np.pi * freq * t) * np.exp(-t * 60)
    out /= max(1e-9, np.max(np.abs(out)))
    return np.stack([out, out], axis=1)

def iris(dur: float = 0.9) -> np.ndarray:
    """Iris/wipe: whoosh panjang dengan pitch sweep turun + shimmer."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * (1400 - 900 * t / dur) * t)
    rng = np.random.default_rng(7)
    noise = signal.lfilter(*signal.butter(4, [400 / (SR/2), 3000 / (SR/2)], btype="band"), rng.standard_normal(n))
    out = 0.6 * noise + 0.4 * tone
    out *= _env(n, 0.1, dur - 0.1)
    out /= max(1e-9, np.max(np.abs(out)))
    return np.stack([out, out], axis=1)

def riser(dur: float = 1.2) -> np.ndarray:
    """Riser menuju momen: noise naik + tone pitch naik, diakhiri hening."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    prog = (t / dur) ** 1.5
    tone = np.sin(2 * np.pi * (200 + 900 * prog) * t)
    rng = np.random.default_rng(11)
    noise = rng.standard_normal(n) * 0.5
    out = 0.5 * tone + 0.5 * noise
    env = np.linspace(0, 1, n) ** 2
    out = out * env
    out /= max(1e-9, np.max(np.abs(out)))
    return np.stack([out, out], axis=1)

SFX_LIB = {"whoosh": whoosh, "shutter": shutter, "click": click, "iris": iris, "riser": riser}

def sfx(name: str, **kwargs) -> np.ndarray:
    if name not in SFX_LIB:
        raise ValueError(f"SFX '{name}' tidak ada. Pilihan: {list(SFX_LIB)}")
    return SFX_LIB[name](**kwargs)

# ─────────── BGM sintetis ───────────

# progression chord: (root freq, chord intervals in semitone ratios)
_CHORDS = {
    "calm": [
        (130.81, [1.0, 1.26, 1.5, 2.0]),   # C maj
        (110.0,  [1.0, 1.26, 1.5, 2.0]),   # A min-ish
        (146.83, [1.0, 1.26, 1.5, 2.0]),   # D
        (123.47, [1.0, 1.19, 1.5, 2.0]),   # G-ish
    ],
    "energetic": [
        (146.83, [1.0, 1.26, 1.5, 2.0]),
        (164.81, [1.0, 1.26, 1.5, 2.0]),
        (130.81, [1.0, 1.26, 1.5, 2.0]),
        (174.61, [1.0, 1.19, 1.5, 2.0]),
    ],
}
_BPM = {"calm": 76, "energetic": 110}

def _chord_note(freq: float, dur_bars: float, amplitude: float = 0.22) -> np.ndarray:
    n = int(dur_bars * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    # pad: sine + sedikit harmonic, envelope lembut
    for mul, amp in [(1.0, 1.0), (2.0, 0.3), (3.0, 0.12)]:
        out += amp * np.sin(2 * np.pi * freq * mul * t)
    env = np.minimum(1.0, np.linspace(0, 8, n)) * np.exp(-t * 0.35)
    return out * env * amplitude

def _kick(t_hit: float, out: np.ndarray):
    n = int(0.15 * SR)
    t = np.arange(n) / SR
    sweep = np.sin(2 * np.pi * (150 - 90 * t / 0.15) * t) * np.exp(-t * 30)
    idx = int(t_hit * SR)
    end = min(len(out), idx + n)
    out[idx:end] += sweep[:end - idx] * 0.35

def _hat(t_hit: float, out: np.ndarray):
    n = int(0.05 * SR)
    rng = np.random.default_rng(int(t_hit * 1000) % 9999)
    h = rng.standard_normal(n) * np.exp(-np.linspace(0, 9, n))
    # highpass
    h = signal.lfilter(*signal.butter(2, 6000 / (SR/2), btype="high"), h)
    idx = int(t_hit * SR)
    end = min(len(out), idx + n)
    out[idx:end] += h[:end - idx] * 0.12

def bgm(duration: float, mood: str = "calm", volume: float = 1.0) -> np.ndarray:
    """Musik latar sintetis: pad chord + kick + hi-hat, loop sepanjang duration."""
    if mood not in _CHORDS:
        raise ValueError(f"mood '{mood}' tidak ada. Pilihan: {list(_CHORDS)}")
    bpm = _BPM[mood]
    bar_sec = (60 / bpm) * 4  # 4 beat per bar
    n = int(duration * SR)
    out = np.zeros(n)
    # pad chord per bar, cycle progression
    ci = 0
    tpos = 0.0
    while tpos < duration:
        root, _ = _CHORDS[mood][ci % len(_CHORDS[mood])]
        seg = min(bar_sec, duration - tpos)
        note = _chord_note(root, seg)
        idx = int(tpos * SR)
        end = min(n, idx + len(note))
        out[idx:end] += note[:end - idx]
        # arpeggio lembut di beat 1 & 3 untuk kalau energetic
        tpos += seg
        ci += 1
    # drum: kick tiap beat, hat di offbeat
    beat = 60 / bpm
    bt = 0.0
    bi = 0
    while bt < duration:
        _kick(bt, out)
        if bi % 2 == 1:
            _hat(bt + beat / 2, out)
        bt += beat
        bi += 1
    out /= max(1e-9, np.max(np.abs(out)))
    out *= volume
    return np.stack([out, out], axis=1)

def write_wav(path: str, audio: np.ndarray, sr: int = SR):
    """Simpan float stereo [-1,1] jadi 16-bit WAV."""
    import wave
    data = np.clip(audio, -1, 1)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
