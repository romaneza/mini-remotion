# Mini-Remotion Engine 🎬

Engine *motion graphics* video berbasis **Python** — semacam Remotion, tapi ringan & hemat token. Cukup Pillow + NumPy + FFmpeg (+ Faster-Whisper buat auto-caption), tanpa Node/React.

Output: MP4 **H.264 + AAC**, default **1080×1920 (vertical) @ 30fps**.

## Fitur

- 🎞️ **Timeline deklaratif** — komposisi dari `Sequence` + transisi fade-out otomatis
- 🧩 **Komponen siap pakai** — `Text`, `Badge`, `ImageBox`, `VStack`, `CaptionHighlight` (subtitle karaoke)
- ✨ **Animasi** — `interpolate()` dengan kurva easing, `spring()` fisik
- 🎙️ **Auto-caption** — ekstraksi timestamp kata per kata via [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper), di-highlight real-time ala TikTok/Reels
- 🔊 **Audio sintetis** — musik latar (2 mood) + SFX (whoosh, shutter, click, iris, riser) dibuat dari nol via NumPy/SciPy, **tanpa aset eksternal**, dengan auto-duck saat voiceover bicara

## Instalasi

```bash
git clone https://github.com/romaneza/mini-remotion.git
cd mini-remotion

python3 -m venv .venv
source .venv/bin/activate
pip install pillow numpy faster-whisper scipy
```

Butuh `ffmpeg` & `ffprobe` di PATH (`brew install ffmpeg` di macOS).

### (Opsional) Wrapper global

Biar perintah `mini-remotion` bisa dipanggil dari folder mana pun:

```bash
mkdir -p ~/.local/bin
cat << 'EOF' > ~/.local/bin/mini-remotion
#!/usr/bin/env bash
ENGINE_DIR="/path/ke/mini-remotion"
PYTHONPATH="$ENGINE_DIR" "$ENGINE_DIR/.venv/bin/python" "$ENGINE_DIR/cli.py" "$@"
EOF
chmod +x ~/.local/bin/mini-remotion
```

## Pemakaian

### 1. Tulis `scene.py`

```python
from engine.core import Composition
from engine.sequence import Sequence
from engine.layout import VStack, Badge, Text

comp = Composition(width=1080, height=1920, fps=30, bg_color=(16, 16, 20))
comp.add_sequence(Sequence(
    start_sec=0.0,
    duration_sec=3.0,
    root=VStack(gap=28, children=[
        Badge("MINI-REMOTION READY", bg_color=(255, 107, 0)),
        Text("Build Engine Berhasil Dijalankan!", size=68, delay_sec=0.15),
        Text("Render motion graphics hemat token.", size=38, color=(170, 170, 180), bold=False, delay_sec=0.4),
    ]),
))
```

### 2. Render / preview

```bash
# Render video (sinkron durasi ke audio, opsional)
python cli.py render scene.py --audio voiceover.mp3 --out output.mp4

# Render + musik latar sintetis + SFX pada detik tertentu (audio final dirakit otomatis)
python cli.py render scene.py --audio vo.mp3 --bgm calm --sfx "whoosh@0.5,click@3.2" --out output.mp4

# Preview 1 frame aja (cepat, buat cek layout)
python cli.py preview scene.py --sec 1.5 --out preview.png
```

### 3. Auto-caption instan

```bash
python cli.py caption --audio voiceover.mp3 --badge "FAKTA" --out caption_output.mp4

# Caption + BGM + SFX sekaligus
python cli.py caption --audio vo.mp3 --badge "FAKTA" --bgm energetic --sfx "iris@0.2,riser@8.0" --out caption.mp4
```

Ini langsung transkrip audio (Whisper, default bahasa Indonesia), pecah per chunk kata, lalu render subtitle karaoke dengan highlight per kata.

## Audio Sintetis (BGM & SFX)

Musik dan efek suara **di-generate dari nol** dengan NumPy/SciPy — tidak perlu file audio tambahan.

**Musik latar** (`--bgm`):
| Mood | Karakter |
|---|---|
| `calm` | Pad chord lembut, kick tipis, BPM 76 — cocok explainer |
| `energetic` | Chord cerah + kick/hat lebih rapat, BPM 110 |

BGM otomatis **di-duck** (volume turun) saat voiceover bicara, naik lagi saat sepi.

**SFX** (`--sfx`, format `nama@detik:volume=x:pan=y`):
| Nama | Suara |
|---|---|
| `whoosh` | Sapuan noise bandpass naik |
| `shutter` | Klik kamera 3 impulse |
| `click` | Pop/tick pendek |
| `iris` | Sweep pitch turun + shimmer (transisi) |
| `riser` | Naik menuju momen penting |

Contoh: `--sfx "whoosh@0.5:volume=0.6,iris@2.0"`

## Referensi API

### Core (`engine.core`)
| | |
|---|---|
| `Composition(width=1080, height=1920, fps=30, bg_color=(16,16,20))` | Wadah utama → `.add_sequence(seq)` |
| `Sequence(start_sec, duration_sec, root, fade_out_sec=0.35)` | Potongan timeline + fade-out |
| `get_audio_duration(path) -> float` | Durasi audio via `ffprobe` |

### Layout (`engine.layout`)
| Komponen | Fungsi |
|---|---|
| `VStack(children, gap=28)` | Susun vertikal, auto center |
| `Text(text, size=56, color, max_width=900, bold=True, align="center", delay_sec=0.0, anim="slide_up"\|"fade"\|None)` | Teks multi-baris + animasi |
| `Badge(label, bg_color=(255,107,0), text_color, size=32, delay_sec=0.0)` | Pill/badge pop-in |
| `ImageBox(image_path, width=860, height=520, radius=28, border_color, border_width, delay_sec=0.0, anim="scale_in"\|"slide_up"\|None)` | Gambar rounded + border |
| `CaptionHighlight(words, size=62, max_width=880, highlight_bg=(255,107,0), align="center")` | Subtitle karaoke per kata |

### Transkripsi (`engine.transcribe`)
| | |
|---|---|
| `extract_word_timestamps(audio_path, model_size="base", language="id") -> list[dict]` | `[{"word", "start", "end"}, ...]` |
| `group_words_into_chunks(words, max_words_per_chunk=6, max_duration_sec=3.2) -> list[dict]` | `[{"start_sec", "duration_sec", "words"}, ...]` |

### Motion (`engine.motion`)
| | |
|---|---|
| `interpolate(frame, (f0,f1), (v0,v1), easing=ease_out_cubic) -> float` | Animasi frame → nilai |
| `spring(frame, fps=30, delay_sec=0.0, damping=12.0, stiffness=180.0) -> float` | Animasi spring 0→1 |
| Easing: `linear`, `ease_out_cubic`, `ease_in_out_cubic` | |

### Audio Sintetis (`engine.audiosynth`)
| | |
|---|---|
| `sfx("whoosh"\|"shutter"\|"click"\|"iris"\|"riser", **kwargs) -> np.ndarray` | Clip SFX stereo `[-1,1]` |
| `bgm(duration, mood="calm"\|"energetic", volume=1.0) -> np.ndarray` | Musik latar loop sepanjang durasi |
| `write_wav(path, audio)` | Simpan array jadi WAV 16-bit stereo |

### Audio Mixing (`engine.mix`)
| | |
|---|---|
| `mix(vo_path, bgm_mood, bgm_volume, sfx_spec, duration, out_path)` | Rakit VO + BGM ducked + SFX → WAV final |
| `auto_duck(bgm, vo)` | Turunkan BGM saat VO aktif (sidechain RMS) |
| `parse_sfx_spec("whoosh@0.5,click@2.0")` | Parse spec SFX jadi list item |

## Pasang sebagai Skill AI (opsional)

Buat `SKILL.md` (contoh ada di repo) dan daftarkan ke direktori skills agent lo (mis. `~/.claude/skills/mini-remotion/SKILL.md`) — jadi agent bisa langsung bikin & render video tanpa ngarang API.

## Lisensi

MIT
