#!/usr/bin/env python3
"""Localize, extract, export, and audit Party Penguin v1."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
ANIMAL = ROOT / "design/runtime/penguin"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
AUDIT = ANIMAL / "audit"
GENERATED = AUDIT / "imagegen"
PUBLIC = ROOT / "public/masks/penguin"
PAGES = ROOT / "github-pages/public/masks/penguin"
STATES = ("neutral", "blink", "roar")
VERSION = "v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def feathered_mask(
    size: tuple[int, int],
    shapes: list[tuple[str, tuple[int, int, int, int], int]],
    blur: float,
) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for kind, box, radius in shapes:
        if kind == "ellipse":
            draw.ellipse(box, fill=255)
        else:
            draw.rounded_rectangle(box, radius=radius, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def fit_square(image: Image.Image, side: int, margin: int = 10) -> Image.Image:
    thumb = image.copy()
    thumb.thumbnail((side - 2 * margin, side - 2 * margin), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(thumb, ((side - thumb.width) // 2, (side - thumb.height) // 2))
    return canvas


def checker(size: tuple[int, int], cell: int = 24) -> Image.Image:
    out = Image.new("RGBA", size, (247, 247, 247, 255))
    draw = ImageDraw.Draw(out)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(210, 210, 216, 255))
    return out


def composite_over(image: Image.Image, background: Image.Image | tuple[int, int, int], side: int = 380) -> Image.Image:
    fitted = fit_square(image, side)
    if isinstance(background, tuple):
        bg = Image.new("RGBA", (side, side), (*background, 255))
    else:
        bg = background.convert("RGBA")
        if bg.size != (side, side):
            bg = bg.resize((side, side), Image.Resampling.BILINEAR)
    bg.alpha_composite(fitted)
    return bg.convert("RGB")


def labeled_sheet(images: list[Image.Image], labels: list[str], columns: int, cell: int = 380) -> Image.Image:
    header = 34
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell, rows * (cell + header)), (28, 28, 34))
    draw = ImageDraw.Draw(sheet)
    for i, image in enumerate(images):
        x = (i % columns) * cell
        y = (i // columns) * (cell + header)
        sheet.paste(image.convert("RGB"), (x, y + header))
        draw.text((x + 10, y + 9), labels[i], fill=(244, 244, 247))
    return sheet


def copy_lighter_mix(states: dict[str, Image.Image], blink: float, roar: float) -> Image.Image:
    weights = np.array([(1.0 - blink) * (1.0 - roar), blink * (1.0 - roar), roar], dtype=np.float32)
    arrays = [np.asarray(states[name].convert("RGBA"), dtype=np.float32) / 255.0 for name in STATES]
    premul = [arr[..., :3] * arr[..., 3:4] for arr in arrays]
    alpha = sum(weights[i] * arrays[i][..., 3:4] for i in range(3))
    rgbp = sum(weights[i] * premul[i] for i in range(3))
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    out = np.concatenate([rgb, alpha], axis=2)
    return Image.fromarray(np.clip(np.rint(out * 255), 0, 255).astype(np.uint8))


def alpha_metrics(image: Image.Image) -> dict[str, object]:
    arr = np.asarray(image.convert("RGBA"))
    alpha = arr[..., 3]
    ys, xs = np.where(alpha > 8)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    pads = [bbox[0], bbox[1], image.width - bbox[2], image.height - bbox[3]]
    weights = alpha.astype(np.float64)
    total = weights.sum()
    centroid = [
        float((weights * np.arange(alpha.shape[1])[None, :]).sum() / total),
        float((weights * np.arange(alpha.shape[0])[:, None]).sum() / total),
    ]

    transparent = alpha == 0
    outside = np.zeros_like(transparent, dtype=bool)
    q: deque[tuple[int, int]] = deque()
    height, width = transparent.shape
    for x in range(width):
        if transparent[0, x]:
            q.append((0, x)); outside[0, x] = True
        if transparent[height - 1, x] and not outside[height - 1, x]:
            q.append((height - 1, x)); outside[height - 1, x] = True
    for y in range(height):
        if transparent[y, 0] and not outside[y, 0]:
            q.append((y, 0)); outside[y, 0] = True
        if transparent[y, width - 1] and not outside[y, width - 1]:
            q.append((y, width - 1)); outside[y, width - 1] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width and transparent[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                q.append((ny, nx))
    holes = transparent & ~outside
    partial = (alpha > 0) & (alpha < 255)
    fringe = partial & (arr[..., 1].astype(np.int16) > arr[..., 0].astype(np.int16) + 20) & (
        arr[..., 1].astype(np.int16) > arr[..., 2].astype(np.int16) + 20
    )
    return {
        "dimensions": [image.width, image.height],
        "bbox_alpha_gt_8": bbox,
        "padding_px_left_top_right_bottom": pads,
        "alpha_weighted_centroid": [round(value, 3) for value in centroid],
        "transparent_corner_alpha": [int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])],
        "partially_transparent_pixels": int(partial.sum()),
        "enclosed_fully_transparent_holes": int(holes.sum()),
        "green_dominant_partial_alpha_pixels": int(fringe.sum()),
    }


def main() -> None:
    for directory in (CHROMA, ALPHA, AUDIT, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    raw = {state: Image.open(GENERATED / f"{state}-{VERSION}.generated.png").convert("RGB") for state in STATES}
    if len({image.size for image in raw.values()}) != 1:
        raise RuntimeError("Generated state dimensions differ")
    size = raw["neutral"].size

    neutral_extracted_path = AUDIT / f"neutral-extracted-{VERSION}.png"
    helper = Path.home() / ".codex/skills/.system/imagegen/scripts/remove_chroma_key.py"
    subprocess.run(
        [
            sys.executable,
            str(helper),
            "--input", str(GENERATED / f"neutral-{VERSION}.generated.png"),
            "--out", str(neutral_extracted_path),
            "--auto-key", "border",
            "--soft-matte",
            "--transparent-threshold", "12",
            "--opaque-threshold", "220",
            "--despill",
            "--force",
        ],
        check=True,
    )
    neutral = Image.open(neutral_extracted_path).convert("RGBA")
    neutral_rgb = neutral.convert("RGB")
    neutral_alpha = neutral.getchannel("A")

    blink_mask = feathered_mask(
        size,
        [
            ("ellipse", (250, 500, 600, 835), 0),
            ("ellipse", (654, 500, 1004, 835), 0),
        ],
        12,
    )
    roar_mask = feathered_mask(
        size,
        [
            ("rounded", (360, 430, 525, 580), 55),
            ("rounded", (729, 430, 894, 580), 55),
            ("ellipse", (485, 675, 770, 960), 0),
        ],
        12,
    )

    # Protect the exterior silhouette and force every state to share the neutral matte.
    safe_interior = neutral_alpha.filter(ImageFilter.MinFilter(41))
    masks = {
        "blink": ImageChops.multiply(blink_mask, safe_interior),
        "roar": ImageChops.multiply(roar_mask, safe_interior),
    }
    for state, mask in masks.items():
        mask.save(AUDIT / f"{state}-localization-mask-{VERSION}.png")

    states: dict[str, Image.Image] = {"neutral": neutral}
    for state in ("blink", "roar"):
        rgb = Image.composite(raw[state], neutral_rgb, masks[state])
        rgba = rgb.convert("RGBA")
        rgba.putalpha(neutral_alpha)
        states[state] = rgba

    # Preserve expression-localized green versions as the project chroma masters.
    for state, image in states.items():
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        green = Image.new("RGBA", size, (0, 255, 0, 255))
        green.alpha_composite(image)
        green.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    candidates: dict[tuple[int, int], list[int]] = {}
    chosen_side: int | None = None
    chosen_quality: int | None = None
    for side in (1254, 1152, 1024):
        for quality in (95, 94):
            sizes: list[int] = []
            for state, image in states.items():
                runtime = image if side == 1254 else image.resize((side, side), Image.Resampling.LANCZOS)
                candidate = AUDIT / f"candidate-{state}-{side}-q{quality}.webp"
                runtime.save(candidate, "WEBP", quality=quality, alpha_quality=100, method=6, exact=True)
                sizes.append(candidate.stat().st_size)
            candidates[(side, quality)] = sizes
            if min(sizes) >= 200_000 and max(sizes) <= 350_000:
                chosen_side, chosen_quality = side, quality
                break
        if chosen_side is not None:
            break
    if chosen_side is None:
        for side in (1254, 1152, 1024):
            for quality in (95, 94):
                if max(candidates[(side, quality)]) <= 350_000:
                    chosen_side, chosen_quality = side, quality
                    break
            if chosen_side is not None:
                break
    if chosen_side is None or chosen_quality is None:
        chosen_side, chosen_quality = 1024, 94

    runtime_states: dict[str, Image.Image] = {}
    for state, image in states.items():
        runtime = image if chosen_side == 1254 else image.resize((chosen_side, chosen_side), Image.Resampling.LANCZOS)
        target = PUBLIC / f"{state}-{VERSION}.webp"
        runtime.save(target, "WEBP", quality=chosen_quality, alpha_quality=100, method=6, exact=True)
        shutil.copy2(target, PAGES / target.name)
        runtime_states[state] = Image.open(target).convert("RGBA")

    native_images: list[Image.Image] = []
    native_labels: list[str] = []
    for state in STATES:
        native_images.append(composite_over(states[state], checker((380, 380)), 380))
        native_labels.append(f"{state} / 380px")
    for state in STATES:
        native_images.append(composite_over(states[state], (232, 237, 244), 96).resize((380, 380), Image.Resampling.NEAREST))
        native_labels.append(f"{state} / 96px (4x)")
    labeled_sheet(native_images, native_labels, 3).save(AUDIT / f"native-and-96-states-{VERSION}.png")

    native_full: list[Image.Image] = []
    native_full_labels: list[str] = []
    for state in STATES:
        native_full.append(composite_over(states[state], checker(size, cell=48), size[0]))
        native_full_labels.append(f"{state} / native {size[0]}px")
    labeled_sheet(native_full, native_full_labels, 3, cell=size[0]).save(
        AUDIT / f"native-states-{VERSION}.jpg", quality=92, optimize=True
    )

    hostile_images: list[Image.Image] = []
    hostile_labels: list[str] = []
    for bg_name, background in (
        ("white", (255, 255, 255)),
        ("near-black", (5, 6, 10)),
        ("navy", (16, 26, 62)),
        ("cyan", (0, 220, 255)),
        ("magenta", (255, 0, 220)),
        ("checker", checker((380, 380))),
    ):
        for state in STATES:
            hostile_images.append(composite_over(runtime_states[state], background, 380))
            hostile_labels.append(f"{state} / {bg_name}")
    labeled_sheet(hostile_images, hostile_labels, 3).save(AUDIT / f"hostile-380-states-{VERSION}.png")

    mixes: list[Image.Image] = []
    mix_labels: list[str] = []
    for label, blink, roar in (
        ("neutral", 0, 0),
        ("blink 25%", .25, 0),
        ("blink 50%", .5, 0),
        ("blink 75%", .75, 0),
        ("blink 100%", 1, 0),
        ("roar 25%", 0, .25),
        ("roar 50%", 0, .5),
        ("roar 75%", 0, .75),
        ("roar 100%", 0, 1),
        ("blink 50 + roar 50", .5, .5),
    ):
        mixes.append(composite_over(copy_lighter_mix(runtime_states, blink, roar), (17, 22, 36), 380))
        mix_labels.append(label)
    labeled_sheet(mixes, mix_labels, 5).save(AUDIT / f"copy-lighter-crossfades-380-{VERSION}.png")

    alpha_hashes = {
        state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
        for state, image in states.items()
    }
    neutral_arr = np.asarray(states["neutral"], dtype=np.int16)
    manifest: dict[str, object] = {
        "animal": "penguin",
        "name": "Party Penguin",
        "version": VERSION,
        "generation_route": "built-in ImageGen neutral using Bumblebee v1 as finish/composition reference; blink and roar edits used neutral as sole target; expression RGB localized onto neutral",
        "runtime_export": {
            "side_px": chosen_side,
            "quality": chosen_quality,
            "alpha_quality": 100,
            "method": 6,
        },
        "candidate_sizes_bytes": {
            f"{side}-q{quality}": values for (side, quality), values in candidates.items()
        },
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "outside_localization_max_channel_delta": {
            state: int(
                np.abs(np.asarray(states[state], dtype=np.int16) - neutral_arr)[np.asarray(masks[state]) == 0].max()
            )
            for state in ("blink", "roar")
        },
        "states": {},
    }
    for state, image in states.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / public_path.name
        decoded = Image.open(public_path).convert("RGBA")
        manifest["states"][state] = {
            "chroma_source": str((GENERATED / f"{state}-{VERSION}.generated.png").relative_to(ROOT)),
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "runtime": str(public_path.relative_to(ROOT)),
            "runtime_bytes": public_path.stat().st_size,
            "runtime_sha256": sha256(public_path),
            "github_pages_sha256": sha256(pages_path),
            "runtime_copies_identical": public_path.read_bytes() == pages_path.read_bytes(),
            "has_alph_chunk": b"ALPH" in public_path.read_bytes(),
            "decoded_alpha_sha256": hashlib.sha256(decoded.getchannel("A").tobytes()).hexdigest(),
            "metrics": alpha_metrics(image),
        }
    (AUDIT / f"manifest-{VERSION}.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
