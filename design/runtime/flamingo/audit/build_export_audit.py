#!/usr/bin/env python3
"""Localize, extract, export, and audit Fancy Flamingo v1."""

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
ANIMAL = ROOT / "design/runtime/flamingo"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
AUDIT = ANIMAL / "audit"
PUBLIC = ROOT / "public/masks/flamingo"
PAGES = ROOT / "github-pages/public/masks/flamingo"
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


def composite_over(
    image: Image.Image,
    background: Image.Image | tuple[int, int, int],
    side: int = 380,
) -> Image.Image:
    fitted = fit_square(image, side)
    if isinstance(background, tuple):
        base = Image.new("RGBA", (side, side), (*background, 255))
    else:
        base = background.convert("RGBA")
        if base.size != (side, side):
            base = base.resize((side, side), Image.Resampling.BILINEAR)
    base.alpha_composite(fitted)
    return base.convert("RGB")


def labeled_sheet(images: list[Image.Image], labels: list[str], columns: int, cell: int = 380) -> Image.Image:
    header = 34
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell, rows * (cell + header)), (28, 28, 34))
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(images):
        x = (index % columns) * cell
        y = (index // columns) * (cell + header)
        sheet.paste(image.convert("RGB"), (x, y + header))
        draw.text((x + 10, y + 9), labels[index], fill=(244, 244, 247))
    return sheet


def copy_lighter_mix(states: dict[str, Image.Image], blink: float, roar: float) -> Image.Image:
    weights = np.array(
        [(1.0 - blink) * (1.0 - roar), blink * (1.0 - roar), roar],
        dtype=np.float32,
    )
    arrays = [np.asarray(states[state].convert("RGBA"), dtype=np.float32) / 255.0 for state in STATES]
    premultiplied = [array[..., :3] * array[..., 3:4] for array in arrays]
    alpha = sum(weights[index] * arrays[index][..., 3:4] for index in range(3))
    rgbp = sum(weights[index] * premultiplied[index] for index in range(3))
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    return Image.fromarray(
        np.clip(np.rint(np.concatenate([rgb, alpha], axis=2) * 255), 0, 255).astype(np.uint8)
    )


def alpha_metrics(image: Image.Image) -> dict[str, object]:
    rgba = np.asarray(image.convert("RGBA"))
    alpha = rgba[..., 3]
    ys, xs = np.where(alpha > 8)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    weights = alpha.astype(np.float64)
    total = weights.sum()
    centroid = [
        float((weights * np.arange(alpha.shape[1])[None, :]).sum() / total),
        float((weights * np.arange(alpha.shape[0])[:, None]).sum() / total),
    ]

    transparent = alpha == 0
    outside = np.zeros_like(transparent, dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    height, width = transparent.shape
    for x in range(width):
        for y in (0, height - 1):
            if transparent[y, x] and not outside[y, x]:
                queue.append((y, x)); outside[y, x] = True
    for y in range(height):
        for x in (0, width - 1):
            if transparent[y, x] and not outside[y, x]:
                queue.append((y, x)); outside[y, x] = True
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width and transparent[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                queue.append((ny, nx))
    partial = (alpha > 0) & (alpha < 255)
    green_fringe = (
        partial
        & (rgba[..., 1].astype(np.int16) > rgba[..., 0].astype(np.int16) + 20)
        & (rgba[..., 1].astype(np.int16) > rgba[..., 2].astype(np.int16) + 20)
    )
    centerline = np.where(alpha[:, image.width // 2] >= 250)[0]
    alpha_380 = np.asarray(image.getchannel("A").resize((380, 380), Image.Resampling.LANCZOS))
    yy, xx = np.ogrid[:380, :380]
    canonical_face = ((xx - 190) / 88.0) ** 2 + ((yy - 200) / 112.0) ** 2 <= 1.0
    canonical_forehead = ((xx - 190) / 78.0) ** 2 + ((yy - 128) / 54.0) ** 2 <= 1.0
    return {
        "dimensions": [image.width, image.height],
        "bbox_alpha_gt_8": bbox,
        "padding_px_left_top_right_bottom": [bbox[0], bbox[1], width - bbox[2], height - bbox[3]],
        "alpha_weighted_centroid": [round(value, 3) for value in centroid],
        "centerline_opaque_span_y": [int(centerline.min()), int(centerline.max())] if centerline.size else None,
        "canonical_face_opaque_coverage_at_380": round(float((alpha_380[canonical_face] >= 250).mean()), 6),
        "canonical_forehead_opaque_coverage_at_380": round(float((alpha_380[canonical_forehead] >= 250).mean()), 6),
        "transparent_corner_alpha": [int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])],
        "partially_transparent_pixels": int(partial.sum()),
        "enclosed_fully_transparent_holes": int((transparent & ~outside).sum()),
        "green_dominant_partial_alpha_pixels": int(green_fringe.sum()),
    }


def main() -> None:
    for directory in (CHROMA, ALPHA, AUDIT, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    raw_paths = {state: CHROMA / f"{state}-raw-{VERSION}.png" for state in STATES}
    raw = {state: Image.open(path).convert("RGB") for state, path in raw_paths.items()}
    if len({image.size for image in raw.values()}) != 1:
        raise RuntimeError("Generated state dimensions differ")
    size = raw["neutral"].size

    extracted_path = AUDIT / f"neutral-extracted-{VERSION}.png"
    helper = Path.home() / ".codex/skills/.system/imagegen/scripts/remove_chroma_key.py"
    subprocess.run(
        [
            sys.executable,
            str(helper),
            "--input", str(raw_paths["neutral"]),
            "--out", str(extracted_path),
            "--auto-key", "border",
            "--soft-matte",
            "--transparent-threshold", "12",
            "--opaque-threshold", "220",
            "--despill",
            "--force",
        ],
        check=True,
    )
    neutral = Image.open(extracted_path).convert("RGBA")
    neutral_rgb = neutral.convert("RGB")
    neutral_alpha = neutral.getchannel("A")

    # Compact masks preserve the generated state semantics while all feathers,
    # silhouette, beak exterior, and non-expression pixels remain byte-identical.
    blink_mask = feathered_mask(
        size,
        [
            ("ellipse", (240, 495, 595, 830), 0),
            ("ellipse", (659, 495, 1014, 830), 0),
        ],
        12,
    )
    roar_mask = feathered_mask(
        size,
        [
            ("rounded", (315, 360, 565, 555), 65),
            ("rounded", (689, 360, 939, 555), 65),
            ("ellipse", (535, 805, 719, 965), 0),
        ],
        12,
    )
    safe_interior = neutral_alpha.filter(ImageFilter.MinFilter(41))
    masks = {
        "blink": ImageChops.multiply(blink_mask, safe_interior),
        "roar": ImageChops.multiply(roar_mask, safe_interior),
    }
    for state, mask in masks.items():
        mask.save(AUDIT / f"{state}-localization-mask-{VERSION}.png")

    states: dict[str, Image.Image] = {"neutral": neutral}
    for state in ("blink", "roar"):
        localized_rgb = Image.composite(raw[state], neutral_rgb, masks[state])
        localized = localized_rgb.convert("RGBA")
        localized.putalpha(neutral_alpha)
        states[state] = localized

    for state, image in states.items():
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        chroma = Image.new("RGBA", size, (0, 255, 0, 255))
        chroma.alpha_composite(image)
        chroma.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

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
        AUDIT / f"native-states-{VERSION}.jpg",
        quality=92,
        optimize=True,
    )

    hostile_images: list[Image.Image] = []
    hostile_labels: list[str] = []
    for background_name, background in (
        ("white", (255, 255, 255)),
        ("near-black", (5, 6, 10)),
        ("navy", (16, 26, 62)),
        ("cyan", (0, 220, 255)),
        ("magenta", (255, 0, 220)),
        ("green", (0, 255, 0)),
        ("checker", checker((380, 380))),
    ):
        for state in STATES:
            hostile_images.append(composite_over(runtime_states[state], background, 380))
            hostile_labels.append(f"{state} / {background_name}")
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
    neutral_array = np.asarray(states["neutral"], dtype=np.int16)
    manifest: dict[str, object] = {
        "animal": "flamingo",
        "name": "Fancy Flamingo",
        "version": VERSION,
        "generation_route": "built-in ImageGen neutral using Bumblebee v1 as finish/composition reference; blink and roar edits used neutral as sole target; expression RGB localized onto neutral",
        "targeted_retries": {"neutral": 0, "blink": 0, "roar": 1},
        "runtime_export": {
            "side_px": chosen_side,
            "quality": chosen_quality,
            "alpha_quality": 100,
            "method": 6,
        },
        "candidate_sizes_bytes": {f"{side}-q{quality}": values for (side, quality), values in candidates.items()},
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "outside_localization_max_channel_delta": {
            state: int(
                np.abs(np.asarray(states[state], dtype=np.int16) - neutral_array)[np.asarray(masks[state]) == 0].max()
            )
            for state in ("blink", "roar")
        },
        "states": {},
    }
    for state, image in states.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        runtime_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / runtime_path.name
        decoded = Image.open(runtime_path).convert("RGBA")
        manifest["states"][state] = {
            "raw_chroma_source": str(raw_paths[state].relative_to(ROOT)),
            "localized_chroma_master": str((CHROMA / f"{state}-{VERSION}.png").relative_to(ROOT)),
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "runtime": str(runtime_path.relative_to(ROOT)),
            "runtime_bytes": runtime_path.stat().st_size,
            "runtime_sha256": sha256(runtime_path),
            "github_pages_sha256": sha256(pages_path),
            "runtime_copies_identical": runtime_path.read_bytes() == pages_path.read_bytes(),
            "has_alph_chunk": b"ALPH" in runtime_path.read_bytes(),
            "decoded_alpha_sha256": hashlib.sha256(decoded.getchannel("A").tobytes()).hexdigest(),
            "metrics": alpha_metrics(image),
        }
    (AUDIT / f"manifest-{VERSION}.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
