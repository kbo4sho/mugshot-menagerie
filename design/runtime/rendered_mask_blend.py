"""Mirror app/rendered-mask-blend.mjs cream×cavity compositing."""

from __future__ import annotations

import numpy as np
from PIL import Image

CAVITY_CHANNEL_MAX = 80
CREAM_CHANNEL_MIN = 160
LAYER_OPENNESS = {
    "neutral": 0,
    "blink": 0,
    "roar-mid": 1,
    "roarMid": 1,
    "roar": 2,
}


def mix_rendered_mask_images(
    states: dict[str, Image.Image],
    weights: dict[str, float],
) -> Image.Image:
    contributing = [key for key, weight in weights.items() if weight > 0 and key in states]
    if not contributing:
        source = next(iter(states.values())).convert("RGBA")
        return Image.new("RGBA", source.size, (0, 0, 0, 0))

    arrays = {
        key: np.asarray(states[key].convert("RGBA"), dtype=np.float32)
        for key in contributing
    }
    alpha = sum(weights[key] * arrays[key][..., 3:4] / 255.0 for key in contributing)
    rgbp = sum(
        weights[key] * arrays[key][..., :3] * (arrays[key][..., 3:4] / 255.0)
        for key in contributing
    )
    rgb = rgbp / np.maximum(alpha, 1e-8)

    most_open = max(contributing, key=lambda key: LAYER_OPENNESS.get(key, 0))
    uses_roar_bridge = any(
        LAYER_OPENNESS.get(key, 0) == 1 and weights.get(key, 0) > 1e-6 for key in contributing
    )
    if uses_roar_bridge:
        most = arrays[most_open]
        most_max = most[..., :3].max(axis=2)
        most_cavity = (most[..., 3] > 16) & (most_max < CAVITY_CHANNEL_MAX)
        most_cream = (most[..., 3] > 16) & (most_max >= CREAM_CHANNEL_MIN)
        disagree = np.zeros(most_max.shape, dtype=bool)
        most_openness = LAYER_OPENNESS.get(most_open, 0)
        for key in contributing:
            if LAYER_OPENNESS.get(key, 0) >= most_openness:
                continue
            less = arrays[key]
            less_max = less[..., :3].max(axis=2)
            less_cavity = (less[..., 3] > 16) & (less_max < CAVITY_CHANNEL_MAX)
            less_cream = (less[..., 3] > 16) & (less_max >= CREAM_CHANNEL_MIN)
            disagree |= (most_cavity & ~less_cavity) | (most_cream & less_cavity)
        rgb[disagree] = most[..., :3][disagree]

    out = np.concatenate((rgb, np.clip(alpha, 0, 1) * 255.0), axis=2)
    return Image.fromarray(np.clip(np.rint(out), 0, 255).astype(np.uint8))
