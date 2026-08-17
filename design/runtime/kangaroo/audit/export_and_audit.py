#!/usr/bin/env python3
"""Localize, harmonize, export, and audit Kooky Kangaroo v1."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
ANIMAL = ROOT / "design/runtime/kangaroo"
AUDIT = ANIMAL / "audit"
RAW = AUDIT / "raw"
ALPHA = ANIMAL / "alpha"
CHROMA = ANIMAL / "chroma"
PUBLIC = ROOT / "public/masks/kangaroo"
PAGES = ROOT / "github-pages/public/masks/kangaroo"
STATES = ("neutral", "blink", "roar-mid", "roar")
VERSION = "v1"
CANVAS = (1254, 1254)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def ellipse_mask(
    size: tuple[int, int],
    boxes: list[tuple[int, int, int, int]],
    blur: float,
) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for box in boxes:
        draw.ellipse(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def localized_state(neutral: Image.Image, source: Image.Image, mask: Image.Image) -> Image.Image:
    output = Image.composite(source.convert("RGB"), neutral.convert("RGB"), mask).convert("RGBA")
    output.putalpha(neutral.getchannel("A"))
    return output


def normalize_roar_cavity(image: Image.Image, raw_source: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Remove the generated red tongue/highlight while preserving the compact O silhouette."""
    source = np.asarray(raw_source.convert("RGB"))
    yy, xx = np.ogrid[:CANVAS[1], :CANVAS[0]]
    roi = (xx >= 565) & (xx < 688) & (yy >= 1075) & (yy < 1192)
    cavity = (
        roi
        & (source[..., 0] < 210)
        & (source[..., 1] < 105)
        & (source[..., 2] < 85)
    )
    cavity_image = Image.fromarray(cavity.astype(np.uint8) * 255)
    cavity_image = cavity_image.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
    warm_cocoa = Image.new("RGB", CANVAS, (64, 24, 18))
    result = Image.composite(warm_cocoa, image.convert("RGB"), cavity_image).convert("RGBA")
    result.putalpha(image.getchannel("A"))
    return result, cavity_image


def exact_green_chroma(image: Image.Image) -> Image.Image:
    field = Image.new("RGBA", image.size, (0, 255, 0, 255))
    field.alpha_composite(image)
    return field.convert("RGB")


def fit_square(image: Image.Image, side: int) -> Image.Image:
    fitted = image.copy()
    fitted.thumbnail((side, side), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(fitted, ((side - fitted.width) // 2, (side - fitted.height) // 2))
    return canvas


def composite_over(image: Image.Image, color: tuple[int, int, int], side: int) -> Image.Image:
    fitted = fit_square(image, side)
    background = Image.new("RGBA", (side, side), (*color, 255))
    background.alpha_composite(fitted)
    return background.convert("RGB")


def contact_sheet(
    images: list[Image.Image], labels: list[str], columns: int, cell: int
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
    if roar <= 0.5:
        roar_mid = roar * 2
        base = 1 - roar_mid
        weights = np.array(
            [(1 - blink) * base, blink * base, roar_mid, 0], dtype=np.float32
        )
    else:
        roar_end = (roar - 0.5) * 2
        weights = np.array([0, 0, 1 - roar_end, roar_end], dtype=np.float32)
    arrays = [np.asarray(states[name], dtype=np.float32) / 255.0 for name in STATES]
    premultiplied = [array[..., :3] * array[..., 3:4] for array in arrays]
    alpha = sum(weights[index] * arrays[index][..., 3:4] for index in range(len(STATES)))
    rgbp = sum(weights[index] * premultiplied[index] for index in range(len(STATES)))
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
        for y in (0, height - 1):
            if transparent[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((y, x))
    for y in range(height):
        for x in (0, width - 1):
            if transparent[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((y, x))
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

    solid = alpha > 8
    seen = np.zeros_like(solid, dtype=bool)
    components = 0
    for y, x in zip(*np.where(solid & ~seen)):
        if seen[y, x]:
            continue
        components += 1
        seen[y, x] = True
        component_queue = deque([(int(y), int(x))])
        while component_queue:
            cy, cx = component_queue.popleft()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = cy + dy, cx + dx
                if (
                    0 <= ny < height
                    and 0 <= nx < width
                    and solid[ny, nx]
                    and not seen[ny, nx]
                ):
                    seen[ny, nx] = True
                    component_queue.append((ny, nx))
    return {
        "dimensions": [image.width, image.height],
        "bbox_alpha_gt_8": bbox,
        "padding_px_left_top_right_bottom": padding,
        "alpha_weighted_centroid": [round(value, 3) for value in centroid],
        "alpha_coverage_fraction": round(float((alpha > 8).mean()), 6),
        "transparent_corner_alpha": [
            int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])
        ],
        "fully_transparent_pixels": int(transparent.sum()),
        "partially_transparent_pixels": int(partial.sum()),
        "enclosed_fully_transparent_holes": int(holes.sum()),
        "connected_components_alpha_gt_8": components,
        "green_dominant_partial_alpha_pixels": int(fringe.sum()),
    }


def chroma_metrics(chroma: Image.Image, alpha: Image.Image) -> dict[str, object]:
    rgb = np.asarray(chroma.convert("RGB"), dtype=np.int16)
    matte = np.asarray(alpha.getchannel("A"))
    field = matte == 0
    key = np.array([0, 255, 0], dtype=np.int16)
    delta = np.abs(rgb[field] - key)
    return {
        "transparent_field_pixels": int(field.sum()),
        "transparent_field_max_channel_delta_from_00ff00": int(delta.max()) if delta.size else 0,
        "corners_rgb": [
            rgb[0, 0].tolist(), rgb[0, -1].tolist(), rgb[-1, 0].tolist(), rgb[-1, -1].tolist()
        ],
    }


def main() -> None:
    for directory in (ALPHA, CHROMA, PUBLIC, PAGES, AUDIT):
        directory.mkdir(parents=True, exist_ok=True)

    neutral = rgba(AUDIT / "extracted-neutral-v1.png")
    blink_source = rgba(AUDIT / "extracted-blink-v1.png")
    roar_mid_source = rgba(AUDIT / "extracted-roar-mid-v1.png")
    roar_source = rgba(AUDIT / "extracted-roar-v1.png")

    blink_mask = ellipse_mask(
        CANVAS,
        [
            (338, 657, 586, 950),
            (666, 657, 914, 950),
            (380, 574, 552, 690),
            (702, 574, 874, 690),
        ],
        10,
    )
    roar_mask = ellipse_mask(
        CANVAS,
        [
            (535, 1037, 713, 1210),
            (380, 566, 552, 690),
            (702, 566, 874, 690),
        ],
        9,
    )
    roar_mid_mask = ellipse_mask(
        CANVAS,
        [
            (548, 1046, 701, 1194),
            (380, 566, 552, 690),
            (702, 566, 874, 690),
        ],
        8,
    )
    blink_mask.save(AUDIT / "blink-localization-mask-v1.png", optimize=True)
    roar_mid_mask.save(AUDIT / "roar-mid-localization-mask-v1.png", optimize=True)
    roar_mask.save(AUDIT / "roar-localization-mask-v1.png", optimize=True)

    blink = localized_state(neutral, blink_source, blink_mask)
    roar_mid = localized_state(neutral, roar_mid_source, roar_mid_mask)
    roar_mid, mid_cavity_mask = normalize_roar_cavity(
        roar_mid, Image.open(RAW / "roar-mid-generated-v1.png")
    )
    roar = localized_state(neutral, roar_source, roar_mask)
    roar, cavity_mask = normalize_roar_cavity(
        roar, Image.open(RAW / "roar-generated-v1.png")
    )
    mid_cavity_mask.save(AUDIT / "roar-mid-cavity-repair-mask-v1.png", optimize=True)
    cavity_mask.save(AUDIT / "roar-cavity-repair-mask-v1.png", optimize=True)
    states = {"neutral": neutral, "blink": blink, "roar-mid": roar_mid, "roar": roar}

    for state, image in states.items():
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        exact_green_chroma(image).save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    candidates: dict[tuple[int, int], list[int]] = {}
    chosen_side: int | None = None
    chosen_quality: int | None = None
    for side in (1254, 1152, 1024):
        for quality in (95, 94):
            sizes: list[int] = []
            for state, image in states.items():
                runtime = image if side == 1254 else image.resize((side, side), Image.Resampling.LANCZOS)
                path = AUDIT / f"candidate-{state}-{side}-q{quality}.webp"
                runtime.save(path, "WEBP", quality=quality, alpha_quality=100, method=6, exact=True)
                sizes.append(path.stat().st_size)
            candidates[(side, quality)] = sizes
            if max(sizes) <= 350_000 and min(sizes) >= 200_000:
                chosen_side, chosen_quality = side, quality
                break
        if chosen_side is not None:
            break
    if chosen_side is None:
        chosen_side, chosen_quality = 1024, 94

    for state, image in states.items():
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

    runtime_states = {state: rgba(PUBLIC / f"{state}-{VERSION}.webp") for state in STATES}

    native = [composite_over(states[state], (235, 240, 246), 1254) for state in STATES]
    contact_sheet(native, [f"{state} / native 1254px" for state in STATES], 4, 1254).save(
        AUDIT / "native-states-v1.png", optimize=True
    )

    review: list[Image.Image] = []
    review_labels: list[str] = []
    for side in (380, 96):
        for state in STATES:
            tile = composite_over(runtime_states[state], (235, 240, 246), side)
            if side == 96:
                tile = tile.resize((380, 380), Image.Resampling.NEAREST)
            review.append(tile)
            review_labels.append(f"{state} / {side}px")
    contact_sheet(review, review_labels, 4, 380).save(AUDIT / "states-380-and-96-v1.png")

    hostile: list[Image.Image] = []
    hostile_labels: list[str] = []
    for name, color in (
        ("white", (255, 255, 255)),
        ("black", (0, 0, 0)),
        ("cyan", (0, 220, 255)),
        ("magenta", (255, 0, 220)),
    ):
        for state in STATES:
            hostile.append(composite_over(runtime_states[state], color, 380))
            hostile_labels.append(f"{state} / {name}")
    contact_sheet(hostile, hostile_labels, 4, 380).save(AUDIT / "hostile-380-states-v1.png")

    scaled = {state: fit_square(runtime_states[state], 380) for state in STATES}
    mixes: list[Image.Image] = []
    mix_labels: list[str] = []
    for label, blink_weight, roar_weight in (
        ("neutral", 0, 0),
        ("blink 25%", 0.25, 0),
        ("blink 50%", 0.5, 0),
        ("blink 75%", 0.75, 0),
        ("blink 100%", 1, 0),
        ("roar bridge 25%", 0, 0.25),
        ("authored roar-mid 50%", 0, 0.5),
        ("roar bridge 75%", 0, 0.75),
        ("roar 100%", 0, 1),
        ("blink 50 + roar 25", 0.5, 0.25),
    ):
        mixes.append(composite_over(copy_lighter_mix(scaled, blink_weight, roar_weight), (35, 48, 72), 380))
        mix_labels.append(label)
    contact_sheet(mixes, mix_labels, 5, 380).save(AUDIT / "copy-lighter-crossfades-380-v1.png")

    species_images: list[Image.Image] = [composite_over(runtime_states["neutral"], (235, 240, 246), 380)]
    species_labels = ["kangaroo / neutral"]
    for animal in ("bunny", "deer", "dog"):
        matches = sorted((ROOT / f"public/masks/{animal}").glob("neutral-v*.webp"))
        if matches:
            species_images.append(composite_over(rgba(matches[-1]), (235, 240, 246), 380))
            species_labels.append(f"{animal} / comparison")
    contact_sheet(species_images, species_labels, 4, 380).save(AUDIT / "species-comparison-380-v1.png")
    species_96 = [
        composite_over(image, (235, 240, 246), 96).resize((192, 192), Image.Resampling.NEAREST)
        for image in [runtime_states["neutral"]]
    ]
    for animal in ("bunny", "deer", "dog"):
        matches = sorted((ROOT / f"public/masks/{animal}").glob("neutral-v*.webp"))
        if matches:
            species_96.append(
                composite_over(rgba(matches[-1]), (235, 240, 246), 96).resize((192, 192), Image.Resampling.NEAREST)
            )
    contact_sheet(species_96, species_labels, 4, 192).save(AUDIT / "species-comparison-96-v1.png")

    coverage = composite_over(runtime_states["neutral"], (35, 48, 72), 380)
    coverage_draw = ImageDraw.Draw(coverage)
    metrics = alpha_metrics(states["neutral"])
    x0, y0, x1, y1 = metrics["bbox_alpha_gt_8"]
    scale = 380 / 1254
    coverage_draw.rectangle(
        (round(x0 * scale), round(y0 * scale), round(x1 * scale), round(y1 * scale)),
        outline=(0, 255, 255), width=2
    )
    coverage_draw.ellipse((73, 103, 307, 365), outline=(255, 210, 0), width=2)
    coverage.save(AUDIT / "canonical-coverage-380-v1.png")

    alpha_hashes = {
        state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
        for state, image in states.items()
    }
    neutral_array = np.asarray(neutral, dtype=np.int16)
    blink_outside = np.asarray(blink_mask) == 0
    roar_mid_total_mask = ImageChops.lighter(roar_mid_mask, mid_cavity_mask)
    roar_total_mask = ImageChops.lighter(roar_mask, cavity_mask)
    roar_mid_outside = np.asarray(roar_mid_total_mask) == 0
    roar_outside = np.asarray(roar_total_mask) == 0
    manifest: dict[str, object] = {
        "animal": "kangaroo",
        "name": "Kooky Kangaroo",
        "version": VERSION,
        "generation_route": (
            "built-in ImageGen; neutral used Bumblebee v1 solely as style/finish/composition reference; "
            "one targeted species correction produced the selected neutral; blink and roar edited selected neutral as sole target"
        ),
        "runtime_export": {
            "side_px": chosen_side,
            "quality": chosen_quality,
            "alpha_quality": 100,
            "method": 6,
            "exact": True,
        },
        "candidate_sizes_bytes": {
            f"{side}-q{quality}": sizes for (side, quality), sizes in candidates.items()
        },
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "outside_localization_max_channel_delta": {
            "blink": int(np.abs(np.asarray(blink, dtype=np.int16) - neutral_array)[blink_outside].max()),
            "roar-mid": int(
                np.abs(np.asarray(roar_mid, dtype=np.int16) - neutral_array)[roar_mid_outside].max()
            ),
            "roar": int(np.abs(np.asarray(roar, dtype=np.int16) - neutral_array)[roar_outside].max()),
        },
        "roar_mid_cavity_repair_nonzero_pixels": int((np.asarray(mid_cavity_mask) > 0).sum()),
        "roar_cavity_repair_nonzero_pixels": int((np.asarray(cavity_mask) > 0).sum()),
        "states": {},
    }
    manifest_states: dict[str, object] = {}
    for state, image in states.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        chroma_path = CHROMA / f"{state}-{VERSION}.png"
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / public_path.name
        manifest_states[state] = {
            "imagegen_source": str((RAW / f"{state}-generated-v1.png").relative_to(ROOT)),
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
    (ANIMAL / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
