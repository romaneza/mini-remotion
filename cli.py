import argparse
import importlib.util
import sys
from pathlib import Path
from PIL import Image

from engine.core import Composition, get_audio_duration
from engine.sequence import Sequence
from engine.layout import VStack, Badge, CaptionHighlight
from engine.transcribe import extract_word_timestamps, group_words_into_chunks
from engine.mix import mix as mix_audio
import tempfile, os, subprocess

def load_composition_from_script(script_path: str) -> Composition:
    path = Path(script_path).resolve()
    if not path.exists():
        sys.exit(f"[Error] File tidak ditemukan: {path}")

    spec = importlib.util.spec_from_file_location("user_scene", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(module)

    if not hasattr(module, "comp") or not isinstance(module.comp, Composition):
        sys.exit("[Error] Script harus mendefinisikan variabel global `comp = Composition(...)`")

    return module.comp

def build_final_audio(args, duration: float) -> str | None:
    """Rakit audio final (VO + BGM + SFX) jika ada layer audio sintetis. Return path WAV."""
    if not (args.bgm or args.sfx):
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    mix_audio(
        vo_path=args.audio,
        bgm_mood=args.bgm,
        bgm_volume=args.bgm_volume,
        sfx_spec=args.sfx,
        duration=duration,
        out_path=tmp.name,
    )
    return tmp.name

def cmd_render(args):
    comp = load_composition_from_script(args.script)
    duration = get_audio_duration(args.audio) if args.audio else comp.total_duration
    audio_for_mux = args.audio
    if args.bgm or args.sfx:
        print("Merakit audio (VO + BGM + SFX)...")
        audio_for_mux = build_final_audio(args, duration)
    comp.export(
        output_path=args.out,
        audio_path=audio_for_mux,
        fit_to_audio=bool(args.audio)
    )
    if audio_for_mux and audio_for_mux != args.audio:
        os.unlink(audio_for_mux)

def cmd_preview(args):
    comp = load_composition_from_script(args.script)
    frame_idx = int(args.sec * comp.fps)
    raw_bytes = comp.render_frame(frame_idx)
    img = Image.frombytes("RGB", (comp.width, comp.height), raw_bytes)
    img.save(args.out)
    print(f"Preview detik ke-{args.sec} (frame {frame_idx}) tersimpan -> {args.out}")

def cmd_caption(args):
    words = extract_word_timestamps(
        args.audio,
        model_size=args.model,
        language=args.lang
    )
    chunks = group_words_into_chunks(words, max_words_per_chunk=args.max_words)
    total_dur = get_audio_duration(args.audio)

    if chunks:
        chunks[-1]["duration_sec"] = max(
            chunks[-1]["duration_sec"],
            total_dur - chunks[-1]["start_sec"]
        )

    comp = Composition(width=1080, height=1920, fps=30, bg_color=(16, 16, 20))
    for chunk in chunks:
        children = []
        if args.badge:
            children.append(Badge(args.badge, bg_color=(255, 107, 0)))
        children.append(CaptionHighlight(
            words=chunk["words"],
            size=64,
            max_width=880,
            highlight_bg=(255, 107, 0)
        ))
        comp.add_sequence(Sequence(
            start_sec=chunk["start_sec"],
            duration_sec=chunk["duration_sec"],
            fade_out_sec=0.15,
            root=VStack(gap=36, children=children)
        ))

    audio_for_mux = args.audio
    if args.bgm or args.sfx:
        print("Merakit audio (VO + BGM + SFX)...")
        audio_for_mux = build_final_audio(args, total_dur)
    comp.export(output_path=args.out, audio_path=audio_for_mux, fit_to_audio=True)
    if audio_for_mux and audio_for_mux != args.audio:
        os.unlink(audio_for_mux)

def main():
    parser = argparse.ArgumentParser(prog="mini-remotion", description="CLI Engine Motion Graphics Python")
    sub = parser.add_subparsers(dest="command", required=True)

    p_render = sub.add_parser("render", help="Render script scene menjadi video MP4")
    p_render.add_argument("script", help="Path ke file Python yang mendefinisikan variabel `comp`")
    p_render.add_argument("--audio", default=None, help="Path file audio voiceover (opsional)")
    p_render.add_argument("--out", default="output.mp4", help="Nama file output MP4")
    p_render.add_argument("--bgm", default=None, help="Musik latar sintetis: calm | energetic")
    p_render.add_argument("--bgm-volume", type=float, default=0.35, help="Volume BGM 0.0-1.0 (default 0.35)")
    p_render.add_argument("--sfx", default=None, help='Daftar SFX sintetis: "whoosh@0.5,click@3.2"')
    p_render.set_defaults(func=cmd_render)

    p_prev = sub.add_parser("preview", help="Render 1 frame PNG untuk cek layout cepat")
    p_prev.add_argument("script", help="Path ke file Python yang mendefinisikan variabel `comp`")
    p_prev.add_argument("--sec", type=float, default=1.0, help="Detik yang ingin dipratinjau")
    p_prev.add_argument("--out", default="preview.png", help="Nama file output PNG")
    p_prev.set_defaults(func=cmd_preview)

    p_cap = sub.add_parser("caption", help="Buat video auto-caption langsung dari file audio")
    p_cap.add_argument("--audio", required=True, help="Path file audio")
    p_cap.add_argument("--out", default="caption_output.mp4", help="Nama file output MP4")
    p_cap.add_argument("--badge", default=None, help="Teks badge opsional di atas caption")
    p_cap.add_argument("--model", default="base", help="Ukuran model faster-whisper (tiny/base/small)")
    p_cap.add_argument("--lang", default="id", help="Kode bahasa audio (default: id)")
    p_cap.add_argument("--max-words", type=int, default=6, help="Maksimal kata per layar")
    p_cap.add_argument("--bgm", default=None, help="Musik latar sintetis: calm | energetic")
    p_cap.add_argument("--bgm-volume", type=float, default=0.35, help="Volume BGM 0.0-1.0 (default 0.35)")
    p_cap.add_argument("--sfx", default=None, help='Daftar SFX sintetis: "whoosh@0.5,click@3.2"')
    p_cap.set_defaults(func=cmd_caption)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
