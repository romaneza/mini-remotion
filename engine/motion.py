import math

def clamp(val: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    return max(min_val, min(max_val, val))

def linear(t: float) -> float:
    return clamp(t)

def ease_out_cubic(t: float) -> float:
    t = clamp(t)
    return 1.0 - pow(1.0 - t, 3)

def ease_in_out_cubic(t: float) -> float:
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2

def interpolate(
    frame: int,
    input_range: tuple[int, int],
    output_range: tuple[float, float],
    easing=ease_out_cubic
) -> float:
    start_f, end_f = input_range
    start_v, end_v = output_range
    if frame <= start_f:
        return start_v
    if frame >= end_f:
        return end_v
    progress = (frame - start_f) / (end_f - start_f)
    return start_v + (end_v - start_v) * easing(progress)

def spring(
    frame: int,
    fps: int = 30,
    delay_sec: float = 0.0,
    damping: float = 12.0,
    stiffness: float = 180.0
) -> float:
    t = (frame / fps) - delay_sec
    if t <= 0:
        return 0.0
    omega = math.sqrt(stiffness)
    zeta = damping / (2.0 * omega)
    if zeta < 1.0:
        omega_d = omega * math.sqrt(1.0 - zeta * zeta)
        val = 1.0 - math.exp(-zeta * omega * t) * (
            math.cos(omega_d * t) + (zeta * omega / omega_d) * math.sin(omega_d * t)
        )
    else:
        val = 1.0 - math.exp(-omega * t) * (1.0 + omega * t)
    return val
