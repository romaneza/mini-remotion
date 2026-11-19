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
        Text("Siap merender video motion graphics hemat token di macOS.", size=38, color=(170, 170, 180), bold=False, delay_sec=0.4)
    ])
))
