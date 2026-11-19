---
name: mini-remotion
description: Render video motion graphics MP4 (H.264 + AAC) menggunakan engine Python lokal (Pillow + NumPy + FFmpeg). Gunakan saat membuat video explainer, kinetic typography, atau auto-caption dari audio.
---

# Mini-Remotion Python Engine

JANGAN menulis loop Pillow/FFmpeg manual. Selalu gunakan modul `engine` di direktori kerja ini dan eksekusi lewat `cli.py`.

## Perintah CLI
- **Render video dari script:**
  `python cli.py render scene.py --audio voiceover.mp3 --out output.mp4`
- **Cek visual 1 frame (cepat):**
  `python cli.py preview scene.py --sec 1.2 --out preview.png`
- **Auto-caption instan dari audio:**
  `python cli.py caption --audio voiceover.mp3 --badge "FAKTA" --out output.mp4`

## Aturan Penulisan `scene.py`
1. Wajib mendefinisikan variabel global `comp = Composition(width=1080, height=1920, fps=30, bg_color=(16, 16, 20))`.
2. Jangan memanggil `comp.export()` di dalam `scene.py` jika dijalankan lewat `cli.py render`.
3. Gunakan `get_audio_duration(path)` untuk menyinkronkan durasi adegan dengan file audio.

## Referensi Komponen (`engine`)

### 1. Core & Sequence
- `Composition(width=1080, height=1920, fps=30, bg_color=(16, 16, 20))` -> `.add_sequence(seq)`
- `Sequence(start_sec, duration_sec, root, fade_out_sec=0.35)`
- `get_audio_duration(audio_path) -> float`

### 2. Layout & Visual (`engine.layout`)
- `VStack(children=[...], gap=28)` — Menyusun komponen vertikal otomatis rata tengah.
- `Text(text, size=56, color=(245,245,247), max_width=900, bold=True, align="center", delay_sec=0.0, anim="slide_up")`
- `Badge(label, bg_color=(255,107,0), text_color=(255,255,255), size=32, delay_sec=0.0)`
- `ImageBox(image_path, width=860, height=520, radius=28, delay_sec=0.0, anim="scale_in")`
- `CaptionHighlight(words, size=62, max_width=880, highlight_bg=(255,107,0))`

### 3. Transkripsi Otomatis (`engine.transcribe`)
- `extract_word_timestamps(audio_path, model_size="base", language="id") -> list[dict]`
- `group_words_into_chunks(words, max_words_per_chunk=6, max_duration_sec=3.2) -> list[dict]`

### 4. Audio Sintetis (`engine.audiosynth` + `engine.mix`)
Musik & SFX di-generate dari nol (NumPy/SciPy), TANPA file audio eksternal.
- CLI render/caption: `--bgm calm|energetic`, `--bgm-volume 0.35`, `--sfx "whoosh@0.5,click@3.2"`
- SFX tersedia: `whoosh`, `shutter`, `click`, `iris`, `riser` (format `nama@detik:volume=x:pan=y`)
- BGM otomatis di-duck saat voiceover bicara
- API: `sfx(name)`, `bgm(duration, mood, volume)`, `mix(vo_path, bgm_mood, bgm_volume, sfx_spec, duration, out_path)`
