#!/usr/bin/env python3
"""Localize, harmonize, export, and audit Party-Pup Dog v1."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
ANIMAL_ROOT = ROOT / "design/runtime/dog"
AUDIT = ANIMAL_ROOT / "audit"
ALPHA = ANIMAL_ROOT / "alpha"
PUBLIC = ROOT / "public/masks/dog"
PAGES = ROOT / "github-pages/public/masks/dog"
STATES = ("neutral", "blink", "roar")
VERSION = "v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def feathered_mask(size: tuple[int, int], shapes: list[tuple[int, int, int, int]], blur: float) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for box in shapes:
        draw.ellipse(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def localized_state(neutral: Image.Image, source: Image.Image, mask: Image.Image) -> Image.Image:
    # ImageGen variants may subtly regenerate the full coat. Composite only the
    # intended expression region, then force the exact approved neutral alpha.
    result = Image.composite(source.convert("RGB"), neutral.convert("RGB"), mask).convert("RGBA")
    result.putalpha(neutral.getchannel("A"))
    return result


def fit_square(image: Image.Image, side: int, margin: int = 16) -> Image.Image:
    thumb = image.copy()
    thumb.thumbnail((side - 2 * margin, side - 2 * margin), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(thumb, ((side - thumb.width) // 2, (side - thumb.height) // 2))
    return canvas


def composite_over(image: Image.Image, color: tuple[int, int, int], side: int = 380) -> Image.Image:
    fitted = fit_square(image, side, margin=10)
    bg = Image.new("RGBA", (side, side), (*color, 255))
    bg.alpha_composite(fitted)
    return bg.convert("RGB")


def contact_sheet(images: list[Image.Image], columns: int, labels: list[str], cell: int = 380) -> Image.Image:
    rows = (len(images) + columns - 1) // columns
    header = 34
    sheet = Image.new("RGB", (columns * cell, rows * (cell + header)), (28, 28, 34))
    draw = ImageDraw.Draw(sheet)
    for i, image in enumerate(images):
        x = (i % columns) * cell
        y = (i // columns) * (cell + header)
        sheet.paste(image.convert("RGB"), (x, y + header))
        draw.text((x + 10, y + 9), labels[i], fill=(244, 244, 247))
    return sheet


def copy_lighter_mix(states: dict[str, Image.Image], blink: float, roar: float) -> Image.Image:
    # Mirrors runtime weights: neutral=(1-b)*(1-r), blink=b*(1-r), roar=r.
    weights = np.array([(1 - blink) * (1 - roar), blink * (1 - roar), roar], dtype=np.float32)
    arrays = [np.asarray(states[name], dtype=np.float32) / 255.0 for name in STATES]
    premul = [arr[..., :3] * arr[..., 3:4] for arr in arrays]
    alpha = sum(weights[i] * arrays[i][..., 3:4] for i in range(3))
    rgbp = sum(weights[i] * premul[i] for i in range(3))
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    out = np.concatenate([rgb, alpha], axis=2)
    return Image.fromarray(np.clip(np.rint(out * 255), 0, 255).astype(np.uint8))


def alpha_metrics(image: Image.Image) -> dict[str, object]:
    arr = np.asarray(image)
    alpha = arr[..., 3]
    ys, xs = np.where(alpha > 8)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    weights = alpha.astype(np.float64)
    total = weights.sum()
    centroid = [float((weights * np.arange(alpha.shape[1])[None, :]).sum() / total),
                float((weights * np.arange(alpha.shape[0])[:, None]).sum() / total)]
    pads = [bbox[0], bbox[1], image.width - bbox[2], image.height - bbox[3]]

    transparent = alpha == 0
    outside = np.zeros_like(transparent, dtype=bool)
    q: deque[tuple[int, int]] = deque()
    h, w = transparent.shape
    for x in range(w):
        if transparent[0, x]: q.append((0, x)); outside[0, x] = True
        if transparent[h - 1, x] and not outside[h - 1, x]: q.append((h - 1, x)); outside[h - 1, x] = True
    for y in range(h):
        if transparent[y, 0] and not outside[y, 0]: q.append((y, 0)); outside[y, 0] = True
        if transparent[y, w - 1] and not outside[y, w - 1]: q.append((y, w - 1)); outside[y, w - 1] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and transparent[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                q.append((ny, nx))
    holes = transparent & ~outside
    partial = (alpha > 0) & (alpha < 255)
    fringe = partial & (arr[..., 1] > arr[..., 0] + 20) & (arr[..., 1] > arr[..., 2] + 20)
    return {
        "dimensions": [image.width, image.height],
        "bbox_alpha_gt_8": bbox,
        "padding_px_left_top_right_bottom": pads,
        "alpha_weighted_centroid": [round(v, 3) for v in centroid],
        "transparent_corner_alpha": [int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])],
        "partially_transparent_pixels": int(partial.sum()),
        "enclosed_fully_transparent_holes": int(holes.sum()),
        "green_dominant_partial_alpha_pixels": int(fringe.sum()),
    }


def main() -> None:
    for directory in (ALPHA, PUBLIC, PAGES, AUDIT):
        directory.mkdir(parents=True, exist_ok=True)

    extracted = {state: rgba(AUDIT / f"{state}-extracted-{VERSION}.png") for state in STATES}
    neutral = extracted["neutral"]
    size = neutral.size

    # Start below the cream eyebrow patches: the generated blink variant added
    # tiny brow ridges that are outside the requested eye-only expression edit.
    blink_mask = feathered_mask(size, [(274, 515, 592, 802), (662, 515, 980, 802)], 12)
    roar_mask = feathered_mask(size, [(520, 790, 734, 1004), (342, 350, 521, 527), (733, 350, 912, 527)], 18)
    blink_mask.save(AUDIT / f"blink-localization-mask-{VERSION}.png")
    roar_mask.save(AUDIT / f"roar-localization-mask-{VERSION}.png")

    states = {
        "neutral": neutral,
        "blink": localized_state(neutral, extracted["blink"], blink_mask),
        "roar": localized_state(neutral, extracted["roar"], roar_mask),
    }
    for state, image in states.items():
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)

    # Keep the largest common runtime side that meets the requested weight bar.
    chosen_side = None
    chosen_quality = None
    candidates: dict[tuple[int, int], list[int]] = {}
    for side in (1254, 1152, 1024):
        for quality in (95, 94):
            sizes = []
            for state, image in states.items():
                runtime = image if side == 1254 else image.resize((side, side), Image.Resampling.LANCZOS)
                path = AUDIT / f"candidate-{state}-{side}-q{quality}.webp"
                runtime.save(path, "WEBP", quality=quality, method=6, exact=True)
                sizes.append(path.stat().st_size)
            candidates[(side, quality)] = sizes
            if max(sizes) <= 350_000 and min(sizes) >= 200_000:
                chosen_side, chosen_quality = side, quality
                break
        if chosen_side is not None:
            break
    if chosen_side is None:
        # Preserve visual quality if the lower target is missed; enforce upper bar.
        for side in (1254, 1152, 1024):
            for quality in (95, 94):
                if max(candidates[(side, quality)]) <= 350_000:
                    chosen_side, chosen_quality = side, quality
                    break
            if chosen_side is not None:
                break
    if chosen_side is None:
        chosen_side, chosen_quality = 1024, 94

    for state, image in states.items():
        runtime = image if chosen_side == 1254 else image.resize((chosen_side, chosen_side), Image.Resampling.LANCZOS)
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        runtime.save(public_path, "WEBP", quality=chosen_quality, method=6, exact=True)
        shutil.copy2(public_path, PAGES / public_path.name)

    hostile_images: list[Image.Image] = []
    hostile_labels: list[str] = []
    for bg_name, bg in (("white", (255, 255, 255)), ("black", (0, 0, 0)),
                        ("cyan", (0, 220, 255)), ("magenta", (255, 0, 220))):
        for state in STATES:
            hostile_images.append(composite_over(states[state], bg))
            hostile_labels.append(f"{state} / {bg_name}")
    contact_sheet(hostile_images, 3, hostile_labels).save(AUDIT / f"hostile-380-states-{VERSION}.png")

    native = []
    native_labels = []
    for state in STATES:
        native.append(composite_over(states[state], (235, 240, 246), 380))
        native_labels.append(f"{state} / 380px")
    for state in STATES:
        native.append(composite_over(states[state], (235, 240, 246), 96).resize((380, 380), Image.Resampling.NEAREST))
        native_labels.append(f"{state} / 96px (4x)")
    contact_sheet(native, 3, native_labels).save(AUDIT / f"native-and-96-states-{VERSION}.png")

    mixes: list[Image.Image] = []
    mix_labels: list[str] = []
    for label, blink, roar in (("neutral", 0, 0), ("blink 25%", .25, 0), ("blink 50%", .5, 0),
                               ("blink 75%", .75, 0), ("blink 100%", 1, 0), ("roar 25%", 0, .25),
                               ("roar 50%", 0, .5), ("roar 75%", 0, .75), ("roar 100%", 0, 1),
                               ("blink 50 + roar 50", .5, .5)):
        mixes.append(composite_over(copy_lighter_mix(states, blink, roar), (35, 48, 72)))
        mix_labels.append(label)
    contact_sheet(mixes, 5, mix_labels).save(AUDIT / f"copy-lighter-crossfades-380-{VERSION}.png")

    alpha_hashes = {state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
                    for state, image in states.items()}
    neutral_arr = np.asarray(states["neutral"])
    blink_outside = np.asarray(blink_mask) == 0
    roar_outside = np.asarray(roar_mask) == 0
    manifest = {
        "animal": "dog",
        "name": "Party-Pup Dog",
        "version": VERSION,
        "generation_route": "built-in ImageGen; neutral generated with Bumblebee v1 as finish/composition reference; state edits used neutral as sole target",
        "runtime_export": {"side_px": chosen_side, "quality": chosen_quality, "method": 6, "alpha_quality": 100},
        "candidate_sizes_bytes": {f"{side}-q{quality}": values for (side, quality), values in candidates.items()},
        "states": {},
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "outside_localization_max_channel_delta": {
            "blink": int(np.abs(np.asarray(states["blink"], dtype=np.int16) - neutral_arr.astype(np.int16))[blink_outside].max()),
            "roar": int(np.abs(np.asarray(states["roar"], dtype=np.int16) - neutral_arr.astype(np.int16))[roar_outside].max()),
        },
    }
    for state, image in states.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / public_path.name
        manifest["states"][state] = {
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "runtime": str(public_path.relative_to(ROOT)),
            "runtime_bytes": public_path.stat().st_size,
            "runtime_sha256": sha256(public_path),
            "github_pages_sha256": sha256(pages_path),
            "runtime_copies_identical": sha256(public_path) == sha256(pages_path),
            "metrics": alpha_metrics(image),
        }
    (AUDIT / f"manifest-{VERSION}.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
