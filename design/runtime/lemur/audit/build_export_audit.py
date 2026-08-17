#!/usr/bin/env python3
"""Localize, harmonize, export, and audit Loopy Lemur v1."""

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
ANIMAL = ROOT / "design/runtime/lemur"
AUDIT = ANIMAL / "audit"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
PUBLIC = ROOT / "public/masks/lemur"
PAGES = ROOT / "github-pages/public/masks/lemur"
STATES = ("neutral", "blink", "roar")
VERSION = "v1"
CANVAS = (1254, 1254)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rendered_mask_blend import mix_rendered_mask_images


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


def checker(size: tuple[int, int], cell: int = 24) -> Image.Image:
    out = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(out)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            fill = "#d8d8d8" if (x // cell + y // cell) % 2 else "#f7f7f7"
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
    label_height = 34
    sheet = Image.new("RGB", (columns * cell, rows * (cell + label_height)), "#1c1c22")
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(images):
        x = index % columns * cell
        y = index // columns * (cell + label_height)
        sheet.paste(image.convert("RGB"), (x, y + label_height))
        draw.text((x + 10, y + 10), labels[index], fill="#f4f4f7")
    return sheet


def copy_lighter_mix(
    states: dict[str, Image.Image], blink_weight: float, roar_weight: float
) -> Image.Image:
    if roar_weight <= 0.5:
        roar_mid = roar_weight * 2.0
        base = 1.0 - roar_mid
        weights = {
            "neutral": (1.0 - blink_weight) * base,
            "blink": blink_weight * base,
            "roar-mid": roar_mid,
            "roar": 0.0,
        }
    else:
        roar = (roar_weight - 0.5) * 2.0
        weights = {"neutral": 0.0, "blink": 0.0, "roar-mid": 1.0 - roar, "roar": roar}
    arrays = {
        state: np.asarray(states[state], dtype=np.float32) / 255.0 for state in weights
    }
    alpha = sum(weight * arrays[state][..., 3:4] for state, weight in weights.items())
    rgbp = sum(
        weight * arrays[state][..., :3] * arrays[state][..., 3:4]
        for state, weight in weights.items()
    )
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    return Image.fromarray(
        np.clip(np.rint(np.concatenate((rgb, alpha), axis=2) * 255), 0, 255).astype(np.uint8)
    )


def semantic_roar_mix(states: dict[str, Image.Image], roar_weight: float) -> Image.Image:
    """Mirror blendRenderedMaskSample for a pack with roar-mid."""
    if roar_weight <= 0.5:
        weights = {"neutral": 1.0 - roar_weight * 2.0, "roar-mid": roar_weight * 2.0}
    else:
        weights = {"roar-mid": 1.0 - (roar_weight - 0.5) * 2.0, "roar": (roar_weight - 0.5) * 2.0}
    return mix_rendered_mask_images(states, weights)


def alpha_metrics(image: Image.Image) -> dict[str, object]:
    array = np.asarray(image.convert("RGBA"))
    alpha = array[..., 3]
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
    queue: deque[tuple[int, int]] = deque()
    height, width = transparent.shape
    for x in range(width):
        if transparent[0, x]:
            outside[0, x] = True
            queue.append((0, x))
        if transparent[height - 1, x] and not outside[height - 1, x]:
            outside[height - 1, x] = True
            queue.append((height - 1, x))
    for y in range(height):
        if transparent[y, 0] and not outside[y, 0]:
            outside[y, 0] = True
            queue.append((y, 0))
        if transparent[y, width - 1] and not outside[y, width - 1]:
            outside[y, width - 1] = True
            queue.append((y, width - 1))
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
    partial = (alpha > 0) & (alpha < 255)
    green_fringe = (
        partial
        & (array[..., 1].astype(np.int16) > array[..., 0].astype(np.int16) + 28)
        & (array[..., 1].astype(np.int16) > array[..., 2].astype(np.int16) + 28)
    )
    return {
        "dimensions": [image.width, image.height],
        "bbox_alpha_gt_8": bbox,
        "padding_px_left_top_right_bottom": pads,
        "alpha_weighted_centroid": [round(value, 3) for value in centroid],
        "transparent_corner_alpha": [
            int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])
        ],
        "partially_transparent_pixels": int(partial.sum()),
        "enclosed_fully_transparent_holes": int((transparent & ~outside).sum()),
        "green_dominant_partial_alpha_pixels": int(green_fringe.sum()),
    }


def canonical_overlay(image: Image.Image) -> Image.Image:
    out = on_background(image.resize((380, 380), Image.Resampling.LANCZOS), "#eef2f6")
    draw = ImageDraw.Draw(out)
    # The production helper draws the 380 square at (-190, -225). Therefore
    # image-space y=225 is the tracked-face origin and y=305 is the standard jaw.
    draw.line((190, 18, 190, 360), fill="#00b8d9", width=2)
    draw.line((20, 225, 360, 225), fill="#ff3d71", width=2)
    draw.line((20, 305, 360, 305), fill="#ff9f1c", width=3)
    draw.ellipse((112, 178, 128, 194), outline="#7b2cff", width=3)
    draw.ellipse((252, 178, 268, 194), outline="#7b2cff", width=3)
    draw.text((24, 231), "tracked origin", fill="#92204f")
    draw.text((24, 311), "standard jaw", fill="#8a5000")
    return out


def main() -> None:
    for directory in (AUDIT, CHROMA, ALPHA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    generated_paths = {state: AUDIT / f"generated-{state}-{VERSION}.png" for state in STATES}
    generated = {state: Image.open(path).convert("RGB") for state, path in generated_paths.items()}
    if any(image.size != CANVAS for image in generated.values()):
        raise RuntimeError("All generated lemur state sources must be 1254 x 1254")

    extracted_path = AUDIT / f"neutral-extracted-{VERSION}.png"
    helper = Path.home() / ".codex/skills/.system/imagegen/scripts/remove_chroma_key.py"
    subprocess.run(
        [
            sys.executable, str(helper), "--input", str(generated_paths["neutral"]),
            "--out", str(extracted_path), "--auto-key", "border", "--soft-matte",
            "--transparent-threshold", "12", "--opaque-threshold", "220", "--despill",
            "--edge-contract", "1", "--force",
        ],
        check=True,
    )
    neutral = rgba(extracted_path)
    neutral_alpha = neutral.getchannel("A")
    neutral_rgb = neutral.convert("RGB")

    blink_mask = feathered_mask(
        CANVAS, ((210, 435, 590, 880), (664, 435, 1044, 880)), blur=16
    )
    roar_mask = feathered_mask(
        CANVAS,
        ((268, 416, 572, 594), (682, 416, 986, 594), (430, 792, 824, 1138)),
        blur=16,
    )
    safe_interior = neutral_alpha.filter(ImageFilter.MinFilter(31))
    masks = {
        "blink": ImageChops.multiply(blink_mask, safe_interior),
        "roar": ImageChops.multiply(roar_mask, safe_interior),
    }
    for state, mask in masks.items():
        mask.save(AUDIT / f"{state}-localization-mask-{VERSION}.png", optimize=True)

    masters: dict[str, Image.Image] = {"neutral": neutral}
    for state in ("blink", "roar"):
        localized_rgb = Image.composite(generated[state], neutral_rgb, masks[state])
        localized = localized_rgb.convert("RGBA")
        localized.putalpha(neutral_alpha)
        masters[state] = localized

    # A single authored semantic bridge replaces the smile before the final
    # cavity grows, avoiding the neutral-smile/full-O double exposure. It is a
    # deterministic deformation of the localized final roar, not a new draw.
    roar_rgb = masters["roar"].convert("RGB")
    roar_mid_source = neutral_rgb.copy()
    mouth_crop = roar_rgb.crop((510, 902, 744, 1080)).resize(
        (183, 139), Image.Resampling.LANCZOS
    )
    roar_mid_source.paste(mouth_crop, (535, 912))
    mid_mouth_mask = feathered_mask(CANVAS, ((490, 882, 764, 1058),), blur=14)
    brow_mask = feathered_mask(
        CANVAS, ((268, 416, 572, 594), (682, 416, 986, 594)), blur=16
    )
    roar_mid_rgb = Image.composite(roar_mid_source, neutral_rgb, mid_mouth_mask)
    roar_mid_rgb = Image.composite(roar_rgb, roar_mid_rgb, brow_mask)
    roar_mid = roar_mid_rgb.convert("RGBA")
    roar_mid.putalpha(neutral_alpha)
    masters["roar-mid"] = roar_mid
    mid_mouth_mask.save(AUDIT / f"roar-mid-localization-mask-{VERSION}.png", optimize=True)

    for state, image in masters.items():
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        chroma = Image.new("RGBA", CANVAS, "#00ff00")
        chroma.alpha_composite(image)
        chroma.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    candidates: dict[tuple[int, int], list[int]] = {}
    chosen_side: int | None = None
    chosen_quality: int | None = None
    for side in (1254, 1152, 1024, 896):
        for quality in (95, 94):
            sizes: list[int] = []
            for state, image in masters.items():
                runtime = image if side == 1254 else image.resize((side, side), Image.Resampling.LANCZOS)
                path = AUDIT / f"candidate-{state}-{side}-q{quality}.webp"
                runtime.save(path, "WEBP", quality=quality, alpha_quality=100, method=6, exact=True)
                sizes.append(path.stat().st_size)
            candidates[(side, quality)] = sizes
            if min(sizes) >= 200_000 and max(sizes) <= 350_000:
                chosen_side, chosen_quality = side, quality
                break
        if chosen_side is not None:
            break
    if chosen_side is None:
        for side in (1254, 1152, 1024, 896):
            for quality in (95, 94):
                if max(candidates[(side, quality)]) <= 350_000:
                    chosen_side, chosen_quality = side, quality
                    break
            if chosen_side is not None:
                break
    if chosen_side is None or chosen_quality is None:
        raise RuntimeError("No q94-95 lemur export stayed under 350KB")

    runtime_images: dict[str, Image.Image] = {}
    for state, image in masters.items():
        runtime = image if chosen_side == 1254 else image.resize((chosen_side, chosen_side), Image.Resampling.LANCZOS)
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        runtime.save(public_path, "WEBP", quality=chosen_quality, alpha_quality=100, method=6, exact=True)
        shutil.copy2(public_path, PAGES / public_path.name)
        runtime_images[state] = rgba(public_path)

    native = [on_background(masters[state], checker(CANVAS, 48)) for state in STATES]
    labeled_sheet(native, [f"{state} / native" for state in STATES], 3, CANVAS[0]).save(
        AUDIT / f"native-states-{VERSION}.jpg", quality=92, optimize=True
    )

    runtime_380 = {
        state: image.resize((380, 380), Image.Resampling.LANCZOS)
        for state, image in runtime_images.items()
    }
    scales: list[Image.Image] = []
    labels: list[str] = []
    for state in STATES:
        scales.append(on_background(runtime_380[state], "#eef2f6"))
        labels.append(f"{state} / 380px")
    for state in STATES:
        tiny = runtime_images[state].resize((96, 96), Image.Resampling.LANCZOS)
        scales.append(on_background(tiny, "#eef2f6").resize((380, 380), Image.Resampling.NEAREST))
        labels.append(f"{state} / 96px (4x)")
    labeled_sheet(scales, labels, 3, 380).save(
        AUDIT / f"native-96-380-states-{VERSION}.png", optimize=True
    )

    hostile: list[Image.Image] = []
    hostile_labels: list[str] = []
    for name, background in (
        ("white", "#ffffff"), ("black", "#000000"), ("cyan", "#00e8ff"),
        ("magenta", "#ff00dc"), ("green", "#00ff00"), ("checker", checker((380, 380))),
    ):
        for state in STATES:
            hostile.append(on_background(runtime_380[state], background))
            hostile_labels.append(f"{state} / {name}")
    labeled_sheet(hostile, hostile_labels, 3, 380).save(
        AUDIT / f"hostile-380-states-{VERSION}.png", optimize=True
    )

    comparison = [on_background(runtime_380["neutral"], "#eef2f6")]
    comparison_labels = ["LEMUR: white ruff + amber eyes"]
    for animal_id, version, label in (
        ("raccoon", "v1", "raccoon comparison"),
        ("panda", "v2", "panda comparison"),
        ("monkey", "v1", "monkey comparison"),
    ):
        path = ROOT / f"public/masks/{animal_id}/neutral-{version}.webp"
        if path.exists():
            other = rgba(path).resize((380, 380), Image.Resampling.LANCZOS)
            comparison.append(on_background(other, "#eef2f6"))
            comparison_labels.append(label)
    labeled_sheet(comparison, comparison_labels, len(comparison), 380).save(
        AUDIT / f"species-comparison-380-{VERSION}.png", optimize=True
    )

    canonical = [canonical_overlay(runtime_images[state]) for state in STATES]
    labeled_sheet(canonical, [f"{state} / canonical" for state in STATES], 3, 380).save(
        AUDIT / f"canonical-coverage-380-{VERSION}.png", optimize=True
    )

    blends: list[Image.Image] = []
    blend_labels: list[str] = []
    for roar_weight in (0.0, 0.33, 0.67, 1.0):
        for blink_weight in (0.0, 0.33, 0.67, 1.0):
            mix = copy_lighter_mix(runtime_images, blink_weight, roar_weight)
            blends.append(on_background(mix.resize((380, 380), Image.Resampling.LANCZOS), "#233048"))
            blend_labels.append(f"blink {blink_weight:.2f} / roar {roar_weight:.2f}")
    labeled_sheet(blends, blend_labels, 4, 380).save(
        AUDIT / f"copy-lighter-crossfades-380-{VERSION}.png", optimize=True
    )

    semantic: list[Image.Image] = []
    semantic_labels: list[str] = []
    for weight in (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0):
        mix = semantic_roar_mix(runtime_images, weight)
        semantic.append(on_background(mix.resize((380, 380), Image.Resampling.LANCZOS), "#233048"))
        semantic_labels.append(f"semantic roar {weight:.3f}")
    labeled_sheet(semantic, semantic_labels, 3, 380).save(
        AUDIT / f"semantic-roar-crossfade-380-{VERSION}.png", optimize=True
    )

    master_alpha_hashes = {
        state: hashlib.sha256(image.getchannel("A").tobytes()).hexdigest()
        for state, image in masters.items()
    }
    runtime_alpha_hashes = {
        state: hashlib.sha256(image.getchannel("A").tobytes()).hexdigest()
        for state, image in runtime_images.items()
    }
    neutral_array = np.asarray(masters["neutral"].convert("RGB"), dtype=np.int16)
    visible = np.asarray(neutral_alpha) > 0
    stability: dict[str, object] = {}
    for state in ("blink", "roar"):
        state_array = np.asarray(masters[state].convert("RGB"), dtype=np.int16)
        delta = np.max(np.abs(state_array - neutral_array), axis=2)
        changed = (delta > 2) & visible
        ys, xs = np.where(changed)
        outside = np.asarray(masks[state]) == 0
        stability[state] = {
            "changed_visible_pixels": int(changed.sum()),
            "changed_visible_percent": round(float(changed.sum() / visible.sum() * 100), 4),
            "changed_bbox": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
            "outside_localization_max_channel_delta": int(
                np.abs(state_array - neutral_array)[outside].max()
            ),
        }

    manifest: dict[str, object] = {
        "animal": "lemur",
        "name": "Loopy Lemur",
        "version": VERSION,
        "generation_route": "built-in ImageGen; Bumblebee v1 was finish/composition reference only; blink and roar used the generated lemur neutral as sole edit target",
        "chroma_key": "#00ff00",
        "generated_neutral_border_key_detected_by_helper": "#03f905",
        "chroma_master_corners_rekeyed_exactly": "#00ff00",
        "generated_sources": {state: str(path.relative_to(ROOT)) for state, path in generated_paths.items()},
        "deterministic_processing": "installed chroma helper; expression RGB localized; shared neutral alpha; q94-95 WebP exports; identical public and Pages copies",
        "runtime_export": {
            "side_px": chosen_side, "quality": chosen_quality, "method": 6, "alpha_quality": 100
        },
        "candidate_sizes_bytes": {
            f"{side}-q{quality}": values for (side, quality), values in candidates.items()
        },
        "master_alpha_pixel_hashes": master_alpha_hashes,
        "master_alpha_pixel_hashes_identical": len(set(master_alpha_hashes.values())) == 1,
        "runtime_alpha_pixel_hashes": runtime_alpha_hashes,
        "runtime_alpha_pixel_hashes_identical": len(set(runtime_alpha_hashes.values())) == 1,
        "state_stability": stability,
        "species_markers": [
            "huge amber eyes", "white ear and cheek ruff", "charcoal orbital masks",
            "long narrow pale muzzle", "silver-gray crown tuft"
        ],
        "canonical_geometry": {
            "draw_size_px": 380, "draw_x": -190, "draw_y": -225,
            "tracked_origin_image_y": 225, "standard_jaw_image_y": 305
        },
        "audit_evidence": [
            f"design/runtime/lemur/audit/native-states-{VERSION}.jpg",
            f"design/runtime/lemur/audit/native-96-380-states-{VERSION}.png",
            f"design/runtime/lemur/audit/hostile-380-states-{VERSION}.png",
            f"design/runtime/lemur/audit/species-comparison-380-{VERSION}.png",
            f"design/runtime/lemur/audit/canonical-coverage-380-{VERSION}.png",
            f"design/runtime/lemur/audit/copy-lighter-crossfades-380-{VERSION}.png",
            f"design/runtime/lemur/audit/semantic-roar-crossfade-380-{VERSION}.png",
        ],
        "states": {},
    }
    for state, image in masters.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        chroma_path = CHROMA / f"{state}-{VERSION}.png"
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / public_path.name
        manifest["states"][state] = {  # type: ignore[index]
            "chroma": str(chroma_path.relative_to(ROOT)),
            "chroma_sha256": sha256(chroma_path),
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "runtime": str(public_path.relative_to(ROOT)),
            "runtime_bytes": public_path.stat().st_size,
            "runtime_sha256": sha256(public_path),
            "github_pages_sha256": sha256(pages_path),
            "runtime_copies_identical": sha256(public_path) == sha256(pages_path),
            "contains_alph_chunk": b"ALPH" in public_path.read_bytes(),
            "metrics": alpha_metrics(image),
        }
    (AUDIT / f"manifest-{VERSION}.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
