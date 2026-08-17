#!/usr/bin/env python3
"""Localize, harmonize, export, and audit Color-Pop Chameleon v1."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
ANIMAL = ROOT / "design/runtime/chameleon"
AUDIT = ANIMAL / "audit"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
PUBLIC = ROOT / "public/masks/chameleon"
PAGES = ROOT / "github-pages/public/masks/chameleon"
STATES = ("neutral", "blink", "roar-mid", "roar")
VERSION = "v1"
CANVAS = (1254, 1254)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def feathered_ellipses(
    boxes: tuple[tuple[int, int, int, int], ...], blur: float
) -> Image.Image:
    mask = Image.new("L", CANVAS, 0)
    draw = ImageDraw.Draw(mask)
    for box in boxes:
        draw.ellipse(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def checker(size: tuple[int, int], cell: int = 24) -> Image.Image:
    out = Image.new("RGB", size, "#f7f7f7")
    draw = ImageDraw.Draw(out)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill="#d8d8d8")
    return out


def on_background(foreground: Image.Image, background: Image.Image | str) -> Image.Image:
    base = (
        Image.new("RGBA", foreground.size, background)
        if isinstance(background, str)
        else background.convert("RGBA")
    )
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
        sheet.paste(image.convert("RGB").resize((cell, cell), Image.Resampling.LANCZOS), (x, y + label_height))
        draw.text((x + 10, y + 10), labels[index], fill="#f4f4f7")
    return sheet


def copy_lighter_mix(
    states: dict[str, Image.Image], blink_weight: float, roar_weight: float
) -> Image.Image:
    if roar_weight <= 0.5:
        roar_mid = roar_weight * 2.0
        base = 1.0 - roar_mid
        weights = np.array(
            [(1.0 - blink_weight) * base, blink_weight * base, roar_mid, 0.0],
            dtype=np.float32,
        )
    else:
        roar = (roar_weight - 0.5) * 2.0
        weights = np.array([0.0, 0.0, 1.0 - roar, roar], dtype=np.float32)
    arrays = [np.asarray(states[state], dtype=np.float32) / 255.0 for state in STATES]
    alphas = [array[..., 3:4] for array in arrays]
    premultiplied = [array[..., :3] * array[..., 3:4] for array in arrays]
    alpha = sum(weights[index] * alphas[index] for index in range(4))
    rgbp = sum(weights[index] * premultiplied[index] for index in range(4))
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    out = np.concatenate((rgb, alpha), axis=2)
    return Image.fromarray(np.clip(np.rint(out * 255), 0, 255).astype(np.uint8))


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
    partial = (alpha > 0) & (alpha < 255)
    red = array[..., 0].astype(np.int16)
    green = array[..., 1].astype(np.int16)
    blue = array[..., 2].astype(np.int16)
    magenta_fringe = partial & (red > green + 28) & (blue > green + 28)
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
        "magenta_dominant_partial_alpha_pixels": int(magenta_fringe.sum()),
    }


def main() -> None:
    for directory in (AUDIT, CHROMA, ALPHA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    generated_paths = {state: AUDIT / f"generated-{state}-{VERSION}.png" for state in STATES}
    generated = {state: Image.open(path).convert("RGB") for state, path in generated_paths.items()}
    if any(image.size != CANVAS for image in generated.values()):
        raise RuntimeError("All generated chameleon masters must be 1254 x 1254")

    neutral = rgba(AUDIT / f"neutral-extracted-{VERSION}.png")
    neutral_alpha = neutral.getchannel("A")
    neutral_rgb = neutral.convert("RGB")

    # The neutral owns every perimeter and every non-expression pixel. Eye and
    # mouth ellipses are kept well inside the locked silhouette and feathered.
    blink_mask = feathered_ellipses(
        ((142, 444, 523, 874), (731, 444, 1112, 874)), blur=16
    )
    roar_mask = feathered_ellipses(((498, 850, 756, 1089),), blur=16)
    safe_interior = neutral_alpha.filter(ImageFilter.MinFilter(41))
    masks = {
        "blink": ImageChops.multiply(blink_mask, safe_interior),
        "roar-mid": ImageChops.multiply(roar_mask, safe_interior),
        "roar": ImageChops.multiply(roar_mask, safe_interior),
    }
    for state, mask in masks.items():
        mask.save(AUDIT / f"{state}-localization-mask-{VERSION}.png", optimize=True)

    masters: dict[str, Image.Image] = {"neutral": neutral}
    for state in ("blink", "roar-mid", "roar"):
        localized_rgb = Image.composite(generated[state], neutral_rgb, masks[state])
        localized = localized_rgb.convert("RGBA")
        localized.putalpha(neutral_alpha)
        masters[state] = localized

    for state, image in masters.items():
        image.putalpha(neutral_alpha)
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        keyed = Image.new("RGBA", CANVAS, "#ff00ff")
        keyed.alpha_composite(image)
        keyed.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    candidates: dict[tuple[int, int], list[int]] = {}
    chosen: tuple[int, int] | None = None
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
                chosen = (side, quality)
                break
        if chosen:
            break
    if chosen is None:
        for side in (1254, 1152, 1024, 896):
            for quality in (95, 94):
                if max(candidates[(side, quality)]) <= 350_000:
                    chosen = (side, quality)
                    break
            if chosen:
                break
    if chosen is None:
        raise RuntimeError("No q94-95 runtime export stayed under 350KB")
    side, quality = chosen

    runtime_images: dict[str, Image.Image] = {}
    for state, image in masters.items():
        runtime = image if side == 1254 else image.resize((side, side), Image.Resampling.LANCZOS)
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        runtime.save(public_path, "WEBP", quality=quality, alpha_quality=100, method=6, exact=True)
        shutil.copy2(public_path, PAGES / public_path.name)
        runtime_images[state] = rgba(public_path)

    native = [on_background(masters[state], checker(CANVAS, 48)) for state in STATES]
    labeled_sheet(native, [f"{state} / native" for state in STATES], 4, CANVAS[0]).save(
        AUDIT / f"native-states-{VERSION}.jpg", quality=92, optimize=True
    )

    runtime_380 = {
        state: image.resize((380, 380), Image.Resampling.LANCZOS)
        for state, image in runtime_images.items()
    }
    scale_images: list[Image.Image] = []
    scale_labels: list[str] = []
    for state in STATES:
        scale_images.append(on_background(runtime_380[state], "#eef2f6"))
        scale_labels.append(f"{state} / 380px")
    for state in STATES:
        tiny = runtime_images[state].resize((96, 96), Image.Resampling.LANCZOS)
        scale_images.append(on_background(tiny, "#eef2f6").resize((380, 380), Image.Resampling.NEAREST))
        scale_labels.append(f"{state} / 96px (4x)")
    labeled_sheet(scale_images, scale_labels, 4, 380).save(
        AUDIT / f"native-96-380-states-{VERSION}.png", optimize=True
    )

    hostile_images: list[Image.Image] = []
    hostile_labels: list[str] = []
    backgrounds: list[tuple[str, Image.Image | str]] = [
        ("white", "#ffffff"), ("black", "#000000"), ("cyan", "#00e8ff"),
        ("magenta", "#ff00dc"), ("green", "#00ff00"), ("checker", checker((380, 380))),
    ]
    for name, background in backgrounds:
        for state in STATES:
            hostile_images.append(on_background(runtime_380[state], background))
            hostile_labels.append(f"{state} / {name}")
    labeled_sheet(hostile_images, hostile_labels, 4, 380).save(
        AUDIT / f"hostile-380-states-{VERSION}.png", optimize=True
    )

    blend_images: list[Image.Image] = []
    blend_labels: list[str] = []
    for roar_weight in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        mix = copy_lighter_mix(runtime_images, 0.0, roar_weight)
        blend_images.append(on_background(mix.resize((380, 380), Image.Resampling.LANCZOS), "#233048"))
        blend_labels.append(f"roar {roar_weight:.1f}")
    for blink_weight in (0.25, 0.5, 0.75, 1.0):
        mix = copy_lighter_mix(runtime_images, blink_weight, 0.0)
        blend_images.append(on_background(mix.resize((380, 380), Image.Resampling.LANCZOS), "#233048"))
        blend_labels.append(f"blink {blink_weight:.2f}")
    labeled_sheet(blend_images, blend_labels, 5, 380).save(
        AUDIT / f"copy-lighter-crossfades-380-{VERSION}.png", optimize=True
    )

    frog_path = ROOT / "public/masks/frog/neutral-v1.webp"
    comparison = [on_background(runtime_380["neutral"], "#eef2f6")]
    labels = ["Color-Pop Chameleon: casque + turret eyes"]
    if frog_path.exists():
        frog = rgba(frog_path).resize((380, 380), Image.Resampling.LANCZOS)
        comparison.append(on_background(frog, "#eef2f6"))
        labels.append("Disco Frog comparison")
    labeled_sheet(comparison, labels, len(comparison), 380).save(
        AUDIT / f"species-comparison-380-{VERSION}.png", optimize=True
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
    stability: dict[str, dict[str, object]] = {}
    for state in ("blink", "roar-mid", "roar"):
        state_array = np.asarray(masters[state].convert("RGB"), dtype=np.int16)
        changed = (np.max(np.abs(state_array - neutral_array), axis=2) > 2) & visible
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
        "animal": "chameleon",
        "name": "Color-Pop Chameleon",
        "version": VERSION,
        "generation_route": "built-in ImageGen; Bumblebee v1 was finish/composition reference only; blink, semantic roar midpoint, and roar used generated neutral as sole edit target",
        "semantic_roar_midpoint": "Authored because the three-state neutral-to-roar audit showed a separate smile and O-mouth at early weights.",
        "chroma_key": "#ff00ff",
        "generated_sources_preserved_under_audit": {
            state: f"design/runtime/chameleon/audit/generated-{state}-{VERSION}.png"
            for state in STATES
        },
        "runtime_export": {
            "side_px": side, "quality": quality, "method": 6, "alpha_quality": 100
        },
        "candidate_sizes_bytes": {
            f"{candidate_side}-q{candidate_quality}": sizes
            for (candidate_side, candidate_quality), sizes in candidates.items()
        },
        "master_alpha_pixel_hashes": master_alpha_hashes,
        "master_alpha_pixel_hashes_identical": len(set(master_alpha_hashes.values())) == 1,
        "runtime_alpha_pixel_hashes": runtime_alpha_hashes,
        "runtime_alpha_pixel_hashes_identical": len(set(runtime_alpha_hashes.values())) == 1,
        "state_stability": stability,
        "species_read": {
            "chameleon_markers": ["tall casque ridge", "paired turret-eye domes", "pebbled reptile skin", "curled cheek silhouette"],
            "frog_confusion_check": "Compared against shipped Disco Frog; chameleon keeps a tall dorsal casque and turret-eye architecture.",
            "lizard_confusion_check": "No generic-lizard pack exists; omission of body/tail plus the casque and turret eyes keeps the face specifically chameleon.",
        },
        "states": {},
        "audit_evidence": [
            f"design/runtime/chameleon/audit/native-states-{VERSION}.jpg",
            f"design/runtime/chameleon/audit/native-96-380-states-{VERSION}.png",
            f"design/runtime/chameleon/audit/hostile-380-states-{VERSION}.png",
            f"design/runtime/chameleon/audit/copy-lighter-crossfades-380-{VERSION}.png",
            f"design/runtime/chameleon/audit/species-comparison-380-{VERSION}.png",
        ],
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
