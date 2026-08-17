#!/usr/bin/env python3
"""Localize, harmonize, export, and audit Sleepy Sloth v1."""

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
ANIMAL = ROOT / "design/runtime/sloth"
AUDIT = ANIMAL / "audit"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
PUBLIC = ROOT / "public/masks/sloth"
PAGES = ROOT / "github-pages/public/masks/sloth"
STATES = ("neutral", "blink", "roar")
VERSION = "v1"
CANVAS = (1254, 1254)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def feathered_mask(
    size: tuple[int, int], boxes: tuple[tuple[int, int, int, int], ...], blur: float
) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for box in boxes:
        draw.ellipse(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def checker(size: tuple[int, int], cell: int = 32) -> Image.Image:
    out = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(out)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            fill = "#d7d9de" if (x // cell + y // cell) % 2 else "#f4f5f7"
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=fill)
    return out


def on_background(foreground: Image.Image, background: Image.Image | str) -> Image.Image:
    if isinstance(background, str):
        base = Image.new("RGBA", foreground.size, background)
    else:
        base = background.convert("RGBA")
    base.alpha_composite(foreground.convert("RGBA"))
    return base.convert("RGB")


def labeled_sheet(
    images: list[Image.Image], labels: list[str], columns: int, cell: int
) -> Image.Image:
    rows = (len(images) + columns - 1) // columns
    header = 34
    sheet = Image.new("RGB", (columns * cell, rows * (cell + header)), "#1c1c22")
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(images):
        x = index % columns * cell
        y = index // columns * (cell + header)
        sheet.paste(image.convert("RGB"), (x, y + header))
        draw.text((x + 10, y + 10), labels[index], fill="#f4f4f7")
    return sheet


def copy_lighter_mix(
    states: dict[str, Image.Image], blink_weight: float, roar_weight: float
) -> Image.Image:
    # Mirrors app/page.tsx: weighted premultiplied copy + lighter offscreen blend.
    weights = np.array(
        [
            (1.0 - blink_weight) * (1.0 - roar_weight),
            blink_weight * (1.0 - roar_weight),
            roar_weight,
        ],
        dtype=np.float32,
    )
    arrays = [np.asarray(states[state], dtype=np.float32) / 255.0 for state in STATES]
    alphas = [array[..., 3:4] for array in arrays]
    premultiplied = [array[..., :3] * array[..., 3:4] for array in arrays]
    alpha = sum(weights[index] * alphas[index] for index in range(3))
    rgbp = sum(weights[index] * premultiplied[index] for index in range(3))
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    out = np.concatenate((rgb, alpha), axis=2)
    return Image.fromarray(np.clip(np.rint(out * 255), 0, 255).astype(np.uint8))


def alpha_metrics(image: Image.Image) -> dict[str, object]:
    array = np.asarray(image.convert("RGBA"))
    alpha = array[..., 3]
    ys, xs = np.where(alpha > 8)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    weights = alpha.astype(np.float64)
    total = weights.sum()
    centroid = [
        float((weights * np.arange(alpha.shape[1])[None, :]).sum() / total),
        float((weights * np.arange(alpha.shape[0])[:, None]).sum() / total),
    ]
    pads = [bbox[0], bbox[1], image.width - bbox[2], image.height - bbox[3]]

    transparent = alpha == 0
    outside = np.zeros_like(transparent, dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    height, width = transparent.shape
    for x in range(width):
        if transparent[0, x]:
            queue.append((0, x))
            outside[0, x] = True
        if transparent[height - 1, x] and not outside[height - 1, x]:
            queue.append((height - 1, x))
            outside[height - 1, x] = True
    for y in range(height):
        if transparent[y, 0] and not outside[y, 0]:
            queue.append((y, 0))
            outside[y, 0] = True
        if transparent[y, width - 1] and not outside[y, width - 1]:
            queue.append((y, width - 1))
            outside[y, width - 1] = True
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if (
                0 <= ny < height
                and 0 <= nx < width
                and transparent[ny, nx]
                and not outside[ny, nx]
            ):
                outside[ny, nx] = True
                queue.append((ny, nx))
    holes = transparent & ~outside
    partial = (alpha > 0) & (alpha < 255)
    green_fringe = (
        partial
        & (array[..., 1].astype(np.int16) > array[..., 0].astype(np.int16) + 20)
        & (array[..., 1].astype(np.int16) > array[..., 2].astype(np.int16) + 20)
    )
    return {
        "dimensions": [image.width, image.height],
        "bbox_alpha_gt_8": bbox,
        "padding_px_left_top_right_bottom": pads,
        "alpha_weighted_centroid": [round(value, 3) for value in centroid],
        "transparent_corner_alpha": [
            int(alpha[0, 0]),
            int(alpha[0, -1]),
            int(alpha[-1, 0]),
            int(alpha[-1, -1]),
        ],
        "partially_transparent_pixels": int(partial.sum()),
        "enclosed_fully_transparent_holes": int(holes.sum()),
        "green_dominant_partial_alpha_pixels": int(green_fringe.sum()),
    }


def main() -> None:
    for directory in (AUDIT, CHROMA, ALPHA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    generated_paths = {state: AUDIT / f"generated-{state}-{VERSION}.png" for state in STATES}
    generated = {state: Image.open(path).convert("RGB") for state, path in generated_paths.items()}
    if any(image.size != CANVAS for image in generated.values()):
        raise RuntimeError("All generated sloth masters must be 1254 x 1254")

    helper = Path.home() / ".codex/skills/.system/imagegen/scripts/remove_chroma_key.py"
    neutral_extracted_path = AUDIT / f"neutral-extracted-{VERSION}.png"
    subprocess.run(
        [
            sys.executable,
            str(helper),
            "--input",
            str(generated_paths["neutral"]),
            "--out",
            str(neutral_extracted_path),
            "--auto-key",
            "border",
            "--soft-matte",
            "--transparent-threshold",
            "12",
            "--opaque-threshold",
            "220",
            "--despill",
            "--edge-contract",
            "1",
            "--force",
        ],
        check=True,
    )
    neutral = rgba(neutral_extracted_path)
    neutral_alpha = neutral.getchannel("A")
    neutral_rgb = neutral.convert("RGB")

    # Keep the generated fur silhouette and facial disks pixel-stable. Blink
    # replaces only the paired eye interiors; roar replaces only mouth + brows.
    blink_mask = feathered_mask(
        CANVAS,
        ((255, 520, 540, 825), (714, 520, 999, 825)),
        blur=16,
    )
    roar_mask = feathered_mask(
        CANVAS,
        ((500, 790, 752, 1010), (300, 440, 485, 555), (770, 440, 955, 555)),
        blur=16,
    )
    safe_interior = neutral_alpha.filter(ImageFilter.MinFilter(41))
    masks = {
        "blink": ImageChops.multiply(blink_mask, safe_interior),
        "roar": ImageChops.multiply(roar_mask, safe_interior),
    }
    for state, mask in masks.items():
        mask.save(AUDIT / f"{state}-localization-mask-{VERSION}.png")

    masters: dict[str, Image.Image] = {"neutral": neutral}
    for state in ("blink", "roar"):
        localized_rgb = Image.composite(generated[state], neutral_rgb, masks[state])
        localized = localized_rgb.convert("RGBA")
        localized.putalpha(neutral_alpha)
        masters[state] = localized

    for state, image in masters.items():
        image.putalpha(neutral_alpha)
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        chroma = Image.new("RGBA", CANVAS, "#00ff00")
        chroma.alpha_composite(image)
        chroma.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    # Prefer the largest q94-95 export whose entire three-state pack stays in
    # the operational 200-350KB band at actual shipped alpha quality.
    candidates: dict[tuple[int, int], list[int]] = {}
    chosen_side: int | None = None
    chosen_quality: int | None = None
    for side in (1254, 1152, 1024, 960, 896):
        for quality in (95, 94):
            sizes: list[int] = []
            for state, image in masters.items():
                runtime = image if side == 1254 else image.resize((side, side), Image.Resampling.LANCZOS)
                path = AUDIT / f"candidate-{state}-{side}-q{quality}.webp"
                runtime.save(
                    path,
                    "WEBP",
                    quality=quality,
                    alpha_quality=100,
                    method=6,
                    exact=True,
                )
                sizes.append(path.stat().st_size)
            candidates[(side, quality)] = sizes
            if min(sizes) >= 200_000 and max(sizes) <= 350_000:
                chosen_side, chosen_quality = side, quality
                break
        if chosen_side is not None:
            break
    if chosen_side is None or chosen_quality is None:
        raise RuntimeError(f"No q94-95 sloth export met the 200-350KB band: {candidates}")

    runtime_images: dict[str, Image.Image] = {}
    for state, image in masters.items():
        runtime = image if chosen_side == 1254 else image.resize((chosen_side, chosen_side), Image.Resampling.LANCZOS)
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        runtime.save(
            public_path,
            "WEBP",
            quality=chosen_quality,
            alpha_quality=100,
            method=6,
            exact=True,
        )
        shutil.copy2(public_path, PAGES / public_path.name)
        runtime_images[state] = rgba(public_path)

    native_images = [on_background(masters[state], checker(CANVAS, 48)) for state in STATES]
    labeled_sheet(native_images, [f"{state} / native" for state in STATES], 3, CANVAS[0]).save(
        AUDIT / f"native-states-{VERSION}.jpg", quality=92, optimize=True
    )

    actual_380 = {
        state: runtime_images[state].resize((380, 380), Image.Resampling.LANCZOS)
        for state in STATES
    }
    actual_96 = {
        state: runtime_images[state].resize((96, 96), Image.Resampling.LANCZOS)
        for state in STATES
    }
    scale_images: list[Image.Image] = []
    scale_labels: list[str] = []
    for state in STATES:
        scale_images.append(on_background(actual_380[state], "#edf0f5"))
        scale_labels.append(f"{state} / 380px")
    for state in STATES:
        preview = on_background(actual_96[state], "#edf0f5").resize((380, 380), Image.Resampling.NEAREST)
        scale_images.append(preview)
        scale_labels.append(f"{state} / 96px (4x)")
    labeled_sheet(scale_images, scale_labels, 3, 380).save(
        AUDIT / f"runtime-380-and-96-states-{VERSION}.png"
    )

    hostile_images: list[Image.Image] = []
    hostile_labels: list[str] = []
    for background_name, background in (
        ("white", "#ffffff"),
        ("black", "#000000"),
        ("cyan", "#00dcff"),
        ("magenta", "#ff00dc"),
    ):
        for state in STATES:
            hostile_images.append(on_background(actual_380[state], background))
            hostile_labels.append(f"{state} / {background_name}")
    labeled_sheet(hostile_images, hostile_labels, 3, 380).save(
        AUDIT / f"hostile-380-states-{VERSION}.png"
    )

    mixes: list[Image.Image] = []
    mix_labels: list[str] = []
    for label, blink_weight, roar_weight in (
        ("neutral", 0.0, 0.0),
        ("blink 25%", 0.25, 0.0),
        ("blink 50%", 0.50, 0.0),
        ("blink 75%", 0.75, 0.0),
        ("blink 100%", 1.0, 0.0),
        ("roar 25%", 0.0, 0.25),
        ("roar 50%", 0.0, 0.50),
        ("roar 75%", 0.0, 0.75),
        ("roar 100%", 0.0, 1.0),
        ("blink 50 + roar 50", 0.50, 0.50),
    ):
        mixed = copy_lighter_mix(actual_380, blink_weight, roar_weight)
        mixes.append(on_background(mixed, "#233048"))
        mix_labels.append(label)
    labeled_sheet(mixes, mix_labels, 5, 380).save(
        AUDIT / f"copy-lighter-crossfades-380-{VERSION}.png"
    )

    neutral_array = np.asarray(masters["neutral"], dtype=np.int16)
    alpha_hashes = {
        state: hashlib.sha256(masters[state].getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }
    manifest: dict[str, object] = {
        "animal": "sloth",
        "name": "Sleepy Sloth",
        "version": VERSION,
        "generation_route": (
            "built-in ImageGen; neutral generated with Bumblebee v1 as finish/composition reference; "
            "blink and roar used neutral as sole edit target"
        ),
        "runtime_export": {
            "side_px": chosen_side,
            "quality": chosen_quality,
            "method": 6,
            "alpha_quality": 100,
        },
        "candidate_sizes_bytes": {
            f"{side}-q{quality}": values
            for (side, quality), values in candidates.items()
        },
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "outside_localization_max_channel_delta": {
            state: int(
                np.abs(np.asarray(masters[state], dtype=np.int16) - neutral_array)[
                    np.asarray(masks[state]) == 0
                ].max()
            )
            for state in ("blink", "roar")
        },
        "states": {},
    }
    for state, image in masters.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        chroma_path = CHROMA / f"{state}-{VERSION}.png"
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / public_path.name
        manifest["states"][state] = {
            "generated_source": str(generated_paths[state].relative_to(ROOT)),
            "generated_sha256": sha256(generated_paths[state]),
            "chroma_master": str(chroma_path.relative_to(ROOT)),
            "chroma_sha256": sha256(chroma_path),
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
