from PIL import Image, ImageDraw, ImageFont, ImageOps
from .motion import spring, interpolate

def load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except IOError:
            continue
    return ImageFont.load_default()

class Component:
    def measure(self, draw: ImageDraw.ImageDraw) -> tuple[int, int]:
        raise NotImplementedError

    def render(self, canvas: Image.Image, x: int, y: int, local_frame: int, fps: int):
        raise NotImplementedError

class Text(Component):
    def __init__(
        self,
        text: str,
        size: int = 56,
        color: tuple[int, int, int] = (245, 245, 247),
        max_width: int = 900,
        line_spacing: int = 14,
        bold: bool = True,
        align: str = "center",
        delay_sec: float = 0.0,
        anim: str = "slide_up"
    ):
        self.text = text
        self.font = load_font(size, bold=bold)
        self.color = color
        self.max_width = max_width
        self.line_spacing = line_spacing
        self.align = align
        self.delay_sec = delay_sec
        self.anim = anim
        self._lines: list[str] = []

    def _wrap_text(self, draw: ImageDraw.ImageDraw) -> list[str]:
        words = self.text.split(" ")
        lines, current_line = [], []
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=self.font)
            if (bbox[2] - bbox[0]) <= self.max_width or not current_line:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
        return lines

    def measure(self, draw: ImageDraw.ImageDraw) -> tuple[int, int]:
        self._lines = self._wrap_text(draw)
        max_w, total_h = 0, 0
        for i, line in enumerate(self._lines):
            bbox = draw.textbbox((0, 0), line, font=self.font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            max_w = max(max_w, w)
            total_h += h + (self.line_spacing if i < len(self._lines) - 1 else 0)
        return max_w, total_h

    def render(self, canvas: Image.Image, x: int, y: int, local_frame: int, fps: int):
        draw = ImageDraw.Draw(canvas, "RGBA")
        if not self._lines:
            self.measure(draw)

        delay_f = int(self.delay_sec * fps)
        if self.anim == "slide_up":
            prog = spring(local_frame, fps=fps, delay_sec=self.delay_sec)
            offset_y = int((1.0 - prog) * 50)
            alpha = int(min(255, max(0, prog * 255)))
        elif self.anim == "fade":
            alpha = int(interpolate(local_frame, (delay_f, delay_f + 15), (0, 255)))
            offset_y = 0
        else:
            alpha, offset_y = 255, 0

        if alpha <= 0:
            return

        curr_y = y + offset_y
        for line in self._lines:
            bbox = draw.textbbox((0, 0), line, font=self.font)
            line_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1]

            if self.align == "center":
                draw_x = x + (self.max_width - line_w) // 2
            elif self.align == "right":
                draw_x = x + (self.max_width - line_w)
            else:
                draw_x = x

            draw.text((draw_x, curr_y), line, font=self.font, fill=(*self.color, alpha))
            curr_y += line_h + self.line_spacing

class Badge(Component):
    def __init__(
        self,
        label: str,
        bg_color: tuple[int, int, int] = (255, 107, 0),
        text_color: tuple[int, int, int] = (255, 255, 255),
        size: int = 32,
        padding: tuple[int, int] = (28, 12),
        delay_sec: float = 0.0
    ):
        self.label = label
        self.bg_color = bg_color
        self.text_color = text_color
        self.font = load_font(size, bold=True)
        self.pad_x, self.pad_y = padding
        self.delay_sec = delay_sec

    def measure(self, draw: ImageDraw.ImageDraw) -> tuple[int, int]:
        bbox = draw.textbbox((0, 0), self.label, font=self.font)
        return (bbox[2] - bbox[0]) + self.pad_x * 2, (bbox[3] - bbox[1]) + self.pad_y * 2

    def render(self, canvas: Image.Image, x: int, y: int, local_frame: int, fps: int):
        draw = ImageDraw.Draw(canvas, "RGBA")
        prog = spring(local_frame, fps=fps, delay_sec=self.delay_sec)
        alpha = int(min(255, max(0, prog * 255)))
        if alpha <= 0:
            return
        w, h = self.measure(draw)
        offset_y = int((1.0 - prog) * 25)
        draw.rounded_rectangle(
            [x, y + offset_y, x + w, y + h + offset_y],
            radius=h // 2,
            fill=(*self.bg_color, alpha)
        )
        draw.text(
            (x + self.pad_x, y + self.pad_y + offset_y - 2),
            self.label,
            font=self.font,
            fill=(*self.text_color, alpha)
        )

class ImageBox(Component):
    def __init__(
        self,
        image_path: str,
        width: int = 860,
        height: int = 540,
        radius: int = 28,
        border_color: tuple[int, int, int] | None = (55, 55, 65),
        border_width: int = 3,
        delay_sec: float = 0.0,
        anim: str = "scale_in"
    ):
        self.width = width
        self.height = height
        self.radius = radius
        self.border_color = border_color
        self.border_width = border_width
        self.delay_sec = delay_sec
        self.anim = anim

        raw_img = Image.open(image_path).convert("RGBA")
        fitted = ImageOps.fit(raw_img, (width, height), method=Image.Resampling.LANCZOS)

        mask = Image.new("L", (width * 2, height * 2), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, width * 2, height * 2], radius=radius * 2, fill=255)
        mask = mask.resize((width, height), Image.Resampling.LANCZOS)

        fitted.putalpha(mask)
        self._prepared_img = fitted

    def measure(self, draw: ImageDraw.ImageDraw) -> tuple[int, int]:
        return self.width, self.height

    def render(self, canvas: Image.Image, x: int, y: int, local_frame: int, fps: int):
        prog = spring(local_frame, fps=fps, delay_sec=self.delay_sec)
        alpha = int(min(255, max(0, prog * 255)))
        if alpha <= 0:
            return

        img_to_paste = self._prepared_img.copy()
        draw_x, draw_y = x, y

        if self.anim == "scale_in":
            scale = 0.88 + 0.12 * prog
            new_w = max(1, int(self.width * scale))
            new_h = max(1, int(self.height * scale))
            img_to_paste = img_to_paste.resize((new_w, new_h), Image.Resampling.LANCZOS)
            draw_x = x + (self.width - new_w) // 2
            draw_y = y + (self.height - new_h) // 2
        elif self.anim == "slide_up":
            draw_y = y + int((1.0 - prog) * 45)

        if alpha < 255:
            r, g, b, a = img_to_paste.split()
            a = a.point(lambda p: int(p * (alpha / 255.0)))
            img_to_paste = Image.merge("RGBA", (r, g, b, a))

        canvas.paste(img_to_paste, (draw_x, draw_y), img_to_paste)

        if self.border_color and self.border_width > 0:
            draw = ImageDraw.Draw(canvas, "RGBA")
            w_curr, h_curr = img_to_paste.size
            draw.rounded_rectangle(
                [draw_x, draw_y, draw_x + w_curr, draw_y + h_curr],
                radius=int(self.radius * (w_curr / self.width)),
                outline=(*self.border_color, alpha),
                width=self.border_width
            )

class CaptionHighlight(Component):
    def __init__(
        self,
        words: list[dict],
        size: int = 58,
        max_width: int = 900,
        word_spacing: int = 16,
        line_spacing: int = 20,
        base_color: tuple[int, int, int] = (230, 230, 235),
        active_text_color: tuple[int, int, int] = (255, 255, 255),
        highlight_bg: tuple[int, int, int] = (255, 107, 0),
        pill_pad: tuple[int, int] = (14, 6),
        pill_radius: int = 14,
        align: str = "center"
    ):
        self.words = words
        self.font = load_font(size, bold=True)
        self.max_width = max_width
        self.word_spacing = word_spacing
        self.line_spacing = line_spacing
        self.base_color = base_color
        self.active_text_color = active_text_color
        self.highlight_bg = highlight_bg
        self.pill_pad_x, self.pill_pad_y = pill_pad
        self.pill_radius = pill_radius
        self.align = align
        self._wrapped_lines: list[list[dict]] = []

    def _layout_words(self, draw: ImageDraw.ImageDraw) -> list[list[dict]]:
        lines: list[list[dict]] = []
        current_line: list[dict] = []
        current_w = 0

        for item in self.words:
            bbox = draw.textbbox((0, 0), item["word"], font=self.font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            word_info = {**item, "w": w, "h": h}

            added_w = w if not current_line else (self.word_spacing + w)
            if current_w + added_w <= self.max_width or not current_line:
                current_line.append(word_info)
                current_w += added_w
            else:
                lines.append(current_line)
                current_line = [word_info]
                current_w = w

        if current_line:
            lines.append(current_line)
        return lines

    def measure(self, draw: ImageDraw.ImageDraw) -> tuple[int, int]:
        self._wrapped_lines = self._layout_words(draw)
        max_w, total_h = 0, 0
        for i, line in enumerate(self._wrapped_lines):
            line_w = sum(w["w"] for w in line) + self.word_spacing * max(0, len(line) - 1)
            line_h = max((w["h"] for w in line), default=0)
            max_w = max(max_w, line_w)
            total_h += line_h + (self.line_spacing if i < len(self._wrapped_lines) - 1 else 0)
        return max_w, total_h

    def render(self, canvas: Image.Image, x: int, y: int, local_frame: int, fps: int):
        draw = ImageDraw.Draw(canvas, "RGBA")
        if not self._wrapped_lines:
            self.measure(draw)

        current_sec = local_frame / fps
        curr_y = y

        for line in self._wrapped_lines:
            line_w = sum(w["w"] for w in line) + self.word_spacing * max(0, len(line) - 1)
            line_h = max((w["h"] for w in line), default=0)

            if self.align == "center":
                curr_x = x + (self.max_width - line_w) // 2
            elif self.align == "right":
                curr_x = x + (self.max_width - line_w)
            else:
                curr_x = x

            for w_info in line:
                is_active = w_info["start"] <= current_sec <= w_info["end"]

                if is_active:
                    draw.rounded_rectangle(
                        [
                            curr_x - self.pill_pad_x,
                            curr_y - self.pill_pad_y,
                            curr_x + w_info["w"] + self.pill_pad_x,
                            curr_y + line_h + self.pill_pad_y + 4
                        ],
                        radius=self.pill_radius,
                        fill=(*self.highlight_bg, 255)
                    )
                    text_color = (*self.active_text_color, 255)
                else:
                    text_color = (*self.base_color, 255)

                draw.text((curr_x, curr_y), w_info["word"], font=self.font, fill=text_color)
                curr_x += w_info["w"] + self.word_spacing

            curr_y += line_h + self.line_spacing

class VStack(Component):
    def __init__(self, children: list[Component], gap: int = 28):
        self.children = children
        self.gap = gap

    def measure(self, draw: ImageDraw.ImageDraw) -> tuple[int, int]:
        max_w, total_h = 0, 0
        for i, child in enumerate(self.children):
            w, h = child.measure(draw)
            max_w = max(max_w, w)
            total_h += h + (self.gap if i < len(self.children) - 1 else 0)
        return max_w, total_h

    def render(self, canvas: Image.Image, x: int, y: int, local_frame: int, fps: int):
        draw = ImageDraw.Draw(canvas, "RGBA")
        _, total_h = self.measure(draw)
        canvas_w, canvas_h = canvas.size

        curr_y = (canvas_h - total_h) // 2
        for child in self.children:
            child_w, child_h = child.measure(draw)
            box_w = child.max_width if isinstance(child, (Text, CaptionHighlight)) else child_w
            child_x = (canvas_w - box_w) // 2
            child.render(canvas, child_x, curr_y, local_frame, fps)
            curr_y += child_h + self.gap
