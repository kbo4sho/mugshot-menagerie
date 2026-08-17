#!/usr/bin/env python3
"""Localize, harmonize, export, and audit Winky Owl v1."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
OWL = ROOT / "design/runtime/owl"
AUDIT = OWL / "audit"
ALPHA = OWL / "alpha"
CHROMA = OWL / "chroma"
PUBLIC = ROOT / "public/masks/owl"
PAGES = ROOT / "github-pages/public/masks/owl"
STATES = ("neutral", "blink", "roar")
VERSION = "v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def expression_mask(
    size: tuple[int, int],
    shapes: list[tuple[int, int, int, int]],
    blur: float,
    protected: list[tuple[int, int, int, int]] | None = None,
) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for box in shapes:
        draw.ellipse(box, fill=255)
    for box in protected or []:
        draw.ellipse(box, fill=0)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def localized_state(neutral: Image.Image, source: Image.Image, mask: Image.Image) -> Image.Image:
    # ImageGen variants retain the character well but regenerate feather maps.
    # Composite only expression islands, then force the neutral matte exactly.
    output = Image.composite(source.convert("RGB"), neutral.convert("RGB"), mask).convert("RGBA")
    output.putalpha(neutral.getchannel("A"))
    return output


def center_scale(image: Image.Image, scale: float) -> Image.Image:
    width, height = image.size
    resized = image.resize(
        (round(width * scale), round(height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    output = np.asarray(
        resized.crop((left, top, left + width, top + height)),
        dtype=np.uint8,
    ).copy()
    # Lanczos can leave sub-3%-alpha rings and resample keyed RGB into a handful
    # of edge pixels. Drop the invisible ring, zero transparent RGB, and despill
    # only objectively green-dominant partial pixels (green is not in this owl).
    output[..., 3][output[..., 3] < 8] = 0
    output[..., :3][output[..., 3] == 0] = 0
    partial = (output[..., 3] > 0) & (output[..., 3] < 255)
    red = output[..., 0].astype(np.int16)
    green = output[..., 1].astype(np.int16)
    blue = output[..., 2].astype(np.int16)
    fringe = partial & (green > red + 20) & (green > blue + 20)
    output[..., 1][fringe] = np.maximum(output[..., 0], output[..., 2])[fringe]
    return Image.fromarray(output)


def exact_green_chroma(image: Image.Image) -> Image.Image:
    field = Image.new("RGBA", image.size, (0, 255, 0, 255))
    field.alpha_composite(image)
    return field.convert("RGB")


def fit_square(image: Image.Image, side: int, margin: int = 0) -> Image.Image:
    thumb = image.copy()
    thumb.thumbnail((side - 2 * margin, side - 2 * margin), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(thumb, ((side - thumb.width) // 2, (side - thumb.height) // 2))
    return canvas


def composite_over(image: Image.Image, color: tuple[int, int, int], side: int = 380) -> Image.Image:
    fitted = fit_square(image, side)
    bg = Image.new("RGBA", (side, side), (*color, 255))
    bg.alpha_composite(fitted)
    return bg.convert("RGB")


def contact_sheet(
    images: list[Image.Image],
    columns: int,
    labels: list[str],
    cell: int = 380,
) -> Image.Image:
    rows = (len(images) + columns - 1) // columns
    header = 34
    sheet = Image.new("RGB", (columns * cell, rows * (cell + header)), (28, 28, 34))
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(images):
        x = (index % columns) * cell
        y = (index // columns) * (cell + header)
        sheet.paste(image.convert("RGB"), (x, y + header))
        draw.text((x + 10, y + 9), labels[index], fill=(244, 244, 247))
    return sheet


def copy_lighter_mix(states: dict[str, Image.Image], blink: float, roar: float) -> Image.Image:
    # Mirrors app/page.tsx exactly:
    # neutral=(1-blink)*(1-roar), blink=blink*(1-roar), roar=roar.
    weights = np.array([(1 - blink) * (1 - roar), blink * (1 - roar), roar], dtype=np.float32)
    arrays = [np.asarray(states[name], dtype=np.float32) / 255.0 for name in STATES]
    premultiplied = [array[..., :3] * array[..., 3:4] for array in arrays]
    alpha = sum(weights[index] * arrays[index][..., 3:4] for index in range(3))
    rgbp = sum(weights[index] * premultiplied[index] for index in range(3))
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    output = np.concatenate([rgb, alpha], axis=2)
    return Image.fromarray(np.clip(np.rint(output * 255), 0, 255).astype(np.uint8))


def alpha_metrics(image: Image.Image) -> dict[str, object]:
    array = np.asarray(image)
    alpha = array[..., 3]
    ys, xs = np.where(alpha > 8)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    weights = alpha.astype(np.float64)
    total = weights.sum()
    centroid = [
        float((weights * np.arange(alpha.shape[1])[None, :]).sum() / total),
        float((weights * np.arange(alpha.shape[0])[:, None]).sum() / total),
    ]
    padding = [bbox[0], bbox[1], image.width - bbox[2], image.height - bbox[3]]

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
    fringe = (
        partial
        & (array[..., 1].astype(np.int16) > array[..., 0].astype(np.int16) + 20)
        & (array[..., 1].astype(np.int16) > array[..., 2].astype(np.int16) + 20)
    )
    return {
        "dimensions": [image.width, image.height],
        "bbox_alpha_gt_8": bbox,
        "padding_px_left_top_right_bottom": padding,
        "alpha_weighted_centroid": [round(value, 3) for value in centroid],
        "transparent_corner_alpha": [
            int(alpha[0, 0]),
            int(alpha[0, -1]),
            int(alpha[-1, 0]),
            int(alpha[-1, -1]),
        ],
        "fully_transparent_pixels": int(transparent.sum()),
        "partially_transparent_pixels": int(partial.sum()),
        "enclosed_fully_transparent_holes": int(holes.sum()),
        "green_dominant_partial_alpha_pixels": int(fringe.sum()),
    }


def chroma_metrics(chroma: Image.Image, alpha: Image.Image) -> dict[str, object]:
    rgb = np.asarray(chroma.convert("RGB"), dtype=np.int16)
    matte = np.asarray(alpha.getchannel("A"))
    exact_background = matte == 0
    key = np.array([0, 255, 0], dtype=np.int16)
    delta = np.abs(rgb[exact_background] - key)
    return {
        "transparent_field_pixels": int(exact_background.sum()),
        "transparent_field_max_channel_delta_from_00ff00": int(delta.max()) if delta.size else 0,
        "corners_rgb": [
            rgb[0, 0].tolist(),
            rgb[0, -1].tolist(),
            rgb[-1, 0].tolist(),
            rgb[-1, -1].tolist(),
        ],
    }


def main() -> None:
    for directory in (ALPHA, CHROMA, PUBLIC, PAGES, AUDIT):
        directory.mkdir(parents=True, exist_ok=True)

    # ImageGen landed slightly smaller than the requested mask footprint. A
    # shared centered 1.08x normalization reaches ~84% width / ~73% height while
    # preserving more than 100 px of side padding and the exact state alignment.
    neutral = center_scale(rgba(AUDIT / "extracted-neutral-edge-v1.png"), 1.08)
    blink_source = center_scale(rgba(AUDIT / "extracted-blink-v1.png"), 1.08)
    roar_source = center_scale(rgba(AUDIT / "extracted-roar-v1.png"), 1.08)
    size = neutral.size

    # Replace the two complete neutral eye islands with the bilateral happy arcs.
    # Protected cheek ovals prevent regenerated blush texture entering the state.
    blink_mask = expression_mask(
        size,
        [(220, 479, 609, 868), (645, 479, 1034, 868)],
        blur=17,
        protected=[(214, 771, 392, 922), (862, 771, 1040, 922)],
    )
    # The roar borrows only the compact open beak and subtle upper-eye brow lift.
    roar_mask = expression_mask(
        size,
        [(517, 684, 738, 970), (263, 425, 571, 609), (683, 425, 991, 609)],
        blur=16,
    )
    blink_mask.save(AUDIT / "blink-localization-mask-v1.png")
    roar_mask.save(AUDIT / "roar-localization-mask-v1.png")

    states = {
        "neutral": neutral,
        "blink": localized_state(neutral, blink_source, blink_mask),
        "roar": localized_state(neutral, roar_source, roar_mask),
    }
    for state, image in states.items():
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        exact_green_chroma(image).save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    # Keep the largest common runtime side that meets the 200–350 KB target.
    candidates: dict[tuple[int, int], list[int]] = {}
    chosen_side: int | None = None
    chosen_quality: int | None = None
    for side in (1254, 1152, 1024):
        for quality in (95, 94):
            sizes: list[int] = []
            for state, image in states.items():
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
            if max(sizes) <= 350_000 and min(sizes) >= 200_000:
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
    if chosen_side is None:
        chosen_side, chosen_quality = 1024, 94

    for state, image in states.items():
        runtime = image if chosen_side == 1254 else image.resize(
            (chosen_side, chosen_side), Image.Resampling.LANCZOS
        )
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

    # All review sheets decode the actual runtime WebPs.
    runtime_states = {state: rgba(PUBLIC / f"{state}-{VERSION}.webp") for state in STATES}

    native_images: list[Image.Image] = []
    native_labels: list[str] = []
    for state in STATES:
        native_images.append(composite_over(runtime_states[state], (235, 240, 246), 380))
        native_labels.append(f"{state} / 380px")
    for state in STATES:
        tiny = composite_over(runtime_states[state], (235, 240, 246), 96)
        native_images.append(tiny.resize((380, 380), Image.Resampling.NEAREST))
        native_labels.append(f"{state} / 96px (4x nearest)")
    contact_sheet(native_images, 3, native_labels).save(AUDIT / "states-380-and-96-v1.png")

    hostile_images: list[Image.Image] = []
    hostile_labels: list[str] = []
    for background_name, background in (
        ("white", (255, 255, 255)),
        ("black", (0, 0, 0)),
        ("cyan", (0, 220, 255)),
        ("magenta", (255, 0, 220)),
    ):
        for state in STATES:
            hostile_images.append(composite_over(runtime_states[state], background, 380))
            hostile_labels.append(f"{state} / {background_name}")
    contact_sheet(hostile_images, 3, hostile_labels).save(AUDIT / "hostile-380-states-v1.png")

    scaled_states = {
        state: fit_square(runtime_states[state], 380) for state in STATES
    }
    mix_images: list[Image.Image] = []
    mix_labels: list[str] = []
    for label, blink, roar in (
        ("neutral", 0, 0),
        ("blink 25%", 0.25, 0),
        ("blink 50%", 0.5, 0),
        ("blink 75%", 0.75, 0),
        ("blink 100%", 1, 0),
        ("roar 25%", 0, 0.25),
        ("roar 50%", 0, 0.5),
        ("roar 75%", 0, 0.75),
        ("roar 100%", 0, 1),
        ("blink 50 + roar 50", 0.5, 0.5),
    ):
        mix_images.append(composite_over(copy_lighter_mix(scaled_states, blink, roar), (35, 48, 72)))
        mix_labels.append(label)
    contact_sheet(mix_images, 5, mix_labels).save(AUDIT / "copy-lighter-crossfades-380-v1.png")

    # Edge closeups: upper-left tuft over black, white, cyan, and magenta.
    edge_images: list[Image.Image] = []
    edge_labels: list[str] = []
    for name, background in (
        ("black", (0, 0, 0)),
        ("white", (255, 255, 255)),
        ("cyan", (0, 220, 255)),
        ("magenta", (255, 0, 220)),
    ):
        composed = composite_over(runtime_states["neutral"], background, chosen_side)
        crop = composed.crop((80, 170, 430, 520)).resize((380, 380), Image.Resampling.NEAREST)
        edge_images.append(crop)
        edge_labels.append(f"upper-left edge / {name}")
    contact_sheet(edge_images, 4, edge_labels).save(AUDIT / "feather-edge-closeups-v1.png")

    alpha_hashes = {
        state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
        for state, image in states.items()
    }
    neutral_array = np.asarray(states["neutral"], dtype=np.int16)
    blink_outside = np.asarray(blink_mask) == 0
    roar_outside = np.asarray(roar_mask) == 0
    manifest: dict[str, object] = {
        "animal": "owl",
        "name": "Winky Owl",
        "version": VERSION,
        "generation_route": (
            "built-in ImageGen; neutral generated with Bumblebee v1 solely as finish/composition "
            "reference; blink and roar each edited from neutral as sole target"
        ),
        "runtime_export": {
            "side_px": chosen_side,
            "quality": chosen_quality,
            "alpha_quality": 100,
            "method": 6,
            "exact": True,
        },
        "candidate_sizes_bytes": {
            f"{side}-q{quality}": values
            for (side, quality), values in candidates.items()
        },
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "localization_mask_nonzero_pixels": {
            "blink": int((np.asarray(blink_mask) > 0).sum()),
            "roar": int((np.asarray(roar_mask) > 0).sum()),
        },
        "outside_localization_max_channel_delta": {
            "blink": int(
                np.abs(np.asarray(states["blink"], dtype=np.int16) - neutral_array)[blink_outside].max()
            ),
            "roar": int(
                np.abs(np.asarray(states["roar"], dtype=np.int16) - neutral_array)[roar_outside].max()
            ),
        },
        "states": {},
    }
    manifest_states: dict[str, object] = {}
    for state, image in states.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        chroma_path = CHROMA / f"{state}-{VERSION}.png"
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / public_path.name
        manifest_states[state] = {
            "imagegen_source": str((AUDIT / f"generated-{state}-{VERSION}.png").relative_to(ROOT)),
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "chroma_master": str(chroma_path.relative_to(ROOT)),
            "chroma_sha256": sha256(chroma_path),
            "runtime": str(public_path.relative_to(ROOT)),
            "runtime_bytes": public_path.stat().st_size,
            "runtime_sha256": sha256(public_path),
            "github_pages_sha256": sha256(pages_path),
            "runtime_copies_identical": sha256(public_path) == sha256(pages_path),
            "alpha_metrics": alpha_metrics(image),
            "chroma_metrics": chroma_metrics(Image.open(chroma_path), image),
        }
    manifest["states"] = manifest_states
    (AUDIT / "manifest-v1.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
