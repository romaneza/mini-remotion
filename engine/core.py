import json
import subprocess
import numpy as np
from PIL import Image
from .sequence import Sequence

def get_audio_duration(audio_path: str) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])

class Composition:
    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        bg_color: tuple[int, int, int] = (18, 18, 22)
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.bg_color = bg_color
        self.sequences: list[Sequence] = []

    def add_sequence(self, seq: Sequence):
        self.sequences.append(seq)

    @property
    def total_duration(self) -> float:
        if not self.sequences:
            return 1.0
        return max(s.start_sec + s.duration_sec for s in self.sequences)

    def render_frame(self, frame_idx: int) -> bytes:
        bg_array = np.full((self.height, self.width, 3), self.bg_color, dtype=np.uint8)
        canvas = Image.fromarray(bg_array, "RGB")

        for seq in self.sequences:
            if seq.is_active(frame_idx, self.fps):
                seq.render(canvas, frame_idx, self.fps)

        return canvas.tobytes()

    def export(
        self,
        output_path: str = "output.mp4",
        audio_path: str | None = None,
        fit_to_audio: bool = True,
        tail_pad_sec: float = 0.25
    ):
        duration = self.total_duration
        if audio_path and fit_to_audio:
            audio_dur = get_audio_duration(audio_path)
            duration = audio_dur + tail_pad_sec

        total_frames = int(duration * self.fps)
        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-pix_fmt", "rgb24",
            "-r", str(self.fps),
            "-i", "-"
        ]
        if audio_path:
            cmd.extend(["-i", audio_path])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p"
        ])
        if audio_path:
            cmd.extend(["-c:a", "aac", "-b:a", "192k", "-t", f"{duration:.3f}"])

        cmd.append(output_path)

        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for frame in range(total_frames):
            proc.stdin.write(self.render_frame(frame))
        proc.stdin.close()
        proc.wait()
        print(f"Render selesai ({duration:.2f}s / {total_frames} frames) -> {output_path}")
