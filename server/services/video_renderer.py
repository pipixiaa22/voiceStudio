import math


def motion_slow_zoom_in(t: float, width: int, height: int, start: float, end: float) -> dict:
    progress = (t - start) / (end - start) if end > start else 0
    scale = 1.0 + 0.15 * progress
    offset_x = (width * scale - width) / 2
    offset_y = (height * scale - height) / 2
    return {
        'scale': scale,
        'position': (-offset_x, -offset_y),
        'size': (int(width * scale), int(height * scale)),
    }


def motion_slow_zoom_out(t: float, width: int, height: int, start: float, end: float) -> dict:
    progress = (t - start) / (end - start) if end > start else 0
    scale = 1.15 - 0.15 * progress
    offset_x = (width * scale - width) / 2
    offset_y = (height * scale - height) / 2
    return {
        'scale': scale,
        'position': (-offset_x, -offset_y),
        'size': (int(width * scale), int(height * scale)),
    }


def motion_pan_left_right(t: float, width: int, height: int, start: float, end: float) -> dict:
    progress = (t - start) / (end - start) if end > start else 0
    scale = 1.2
    pan_range = width * (scale - 1)
    offset_x = pan_range * progress
    return {
        'scale': scale,
        'position': (-offset_x, 0),
        'size': (int(width * scale), int(height * scale)),
    }


def motion_breathing_zoom(t: float, width: int, height: int, start: float, end: float) -> dict:
    progress = (t - start) / (end - start) if end > start else 0
    scale = 1.05 + 0.05 * math.sin(progress * 2 * math.pi)
    offset_x = (width * scale - width) / 2
    offset_y = (height * scale - height) / 2
    return {
        'scale': scale,
        'position': (-offset_x, -offset_y),
        'size': (int(width * scale), int(height * scale)),
    }


def motion_shake(t: float, width: int, height: int, start: float, end: float) -> dict:
    progress = (t - start) / (end - start) if end > start else 0
    intensity = 8 * (1 - progress)
    offset_x = intensity * math.sin(t * 30)
    offset_y = intensity * math.cos(t * 25)
    return {
        'scale': 1.05,
        'position': (offset_x, offset_y),
        'size': (int(width * 1.05), int(height * 1.05)),
    }


def motion_fade_in(t: float, width: int, height: int, start: float, end: float) -> dict:
    return {
        'scale': 1.0,
        'position': (0, 0),
        'size': (width, height),
        'opacity': min(1.0, (t - start) / 0.5) if end - start > 0.5 else 1.0,
    }


MOTION_FUNCTIONS = {
    'slow_zoom_in': motion_slow_zoom_in,
    'slow_zoom_out': motion_slow_zoom_out,
    'pan_left_right': motion_pan_left_right,
    'breathing_zoom': motion_breathing_zoom,
    'shake': motion_shake,
    'fade_in': motion_fade_in,
}


def get_motion_function(motion_key: str):
    return MOTION_FUNCTIONS.get(motion_key, motion_slow_zoom_in)
