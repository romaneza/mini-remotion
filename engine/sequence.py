from PIL import Image
from .layout import Component
from .motion import interpolate, linear

class Sequence:
    def __init__(
        self,
        start_sec: float,
        duration_sec: float,
        root: Component,
        fade_out_sec: float = 0.35
    ):
        self.start_sec = start_sec
        self.duration_sec = duration_sec
        self.root = root
        self.fade_out_sec = fade_out_sec

    def is_active(self, global_frame: int, fps: int) -> bool:
        start_f = int(self.start_sec * fps)
        end_f = int((self.start_sec + self.duration_sec) * fps)
        return start_f <= global_frame < end_f

    def render(self, canvas: Image.Image, global_frame: int, fps: int):
        start_f = int(self.start_sec * fps)
        total_seq_frames = int(self.duration_sec * fps)
        local_frame = global_frame - start_f

        fade_frames = int(self.fade_out_sec * fps)
        fade_start_f = max(0, total_seq_frames - fade_frames)

        if fade_frames <= 0 or local_frame < fade_start_f:
            self.root.render(canvas, 0, 0, local_frame, fps)
            return

        opacity = interpolate(
            local_frame,
            (fade_start_f, total_seq_frames - 1),
            (1.0, 0.0),
            easing=linear
        )
        if opacity <= 0.0:
            return

        temp_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        self.root.render(temp_layer, 0, 0, local_frame, fps)

        r, g, b, a = temp_layer.split()
        a = a.point(lambda p: int(p * opacity))
        faded_layer = Image.merge("RGBA", (r, g, b, a))

        canvas.paste(faded_layer, (0, 0), faded_layer)
