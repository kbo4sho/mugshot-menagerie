#!/usr/bin/env python3
"""Build and audit the critic-directed Color-Pop Chameleon v2 mouth repair."""

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
ALPHA = ANIMAL / "alpha"
CHROMA = ANIMAL / "chroma"
PUBLIC = ROOT / "public/masks/chameleon"
PAGES = ROOT / "github-pages/public/masks/chameleon"
STATES = ("neutral", "blink", "roar-mid", "roar")
VERSION = "v2"
CANVAS = (1254, 1254)
MOUTH_ROI = (492, 874, 762, 1050)


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    out = Image.new("RGB", (columns * cell, rows * (cell + label_height)), "#1c1c22")
    draw = ImageDraw.Draw(out)
    for index, image in enumerate(images):
        x = index % columns * cell
        y = index // columns * (cell + label_height)
        out.paste(image.convert("RGB").resize((cell, cell), Image.Resampling.LANCZOS), (x, y + label_height))
        draw.text((x + 9, y + 10), labels[index], fill="#f4f4f7")
    return out


def helper_mix(states: dict[str, Image.Image], roar_weight: float) -> Image.Image:
    """Exact semantic-roar branch from app/rendered-mask-blend.mjs."""
    if roar_weight <= 0.5:
        mid = roar_weight * 2.0
        weights = np.array([1.0 - mid, 0.0, mid, 0.0], dtype=np.float32)
    else:
        roar = (roar_weight - 0.5) * 2.0
        weights = np.array([0.0, 0.0, 1.0 - roar, roar], dtype=np.float32)
    arrays = [np.asarray(states[state], dtype=np.float32) / 255.0 for state in STATES]
    alphas = [array[..., 3:4] for array in arrays]
    premultiplied = [array[..., :3] * array[..., 3:4] for array in arrays]
    alpha = sum(weights[index] * alphas[index] for index in range(4))
    rgbp = sum(weights[index] * premultiplied[index] for index in range(4))
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    return Image.fromarray(
        np.clip(np.rint(np.concatenate((rgb, alpha), axis=2) * 255), 0, 255).astype(np.uint8)
    )


def connected_components(mask: np.ndarray) -> list[int]:
    """Return four-connected component sizes for a compact boolean mask."""
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    sizes: list[int] = []
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or seen[y, x]:
                continue
            queue: deque[tuple[int, int]] = deque([(y, x)])
            seen[y, x] = True
            size = 0
            while queue:
                cy, cx = queue.popleft()
                size += 1
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = cy + dy, cx + dx
                    if (
                        0 <= ny < height
                        and 0 <= nx < width
                        and mask[ny, nx]
                        and not seen[ny, nx]
                    ):
                        seen[ny, nx] = True
                        queue.append((ny, nx))
            sizes.append(size)
    return sorted(sizes, reverse=True)


def alpha_metrics(image: Image.Image) -> dict[str, object]:
    array = np.asarray(image.convert("RGBA"))
    alpha = array[..., 3]
    ys, xs = np.where(alpha > 8)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    weights = alpha.astype(np.float64)
    total = weights.sum()
    partial = (alpha > 0) & (alpha < 255)
    red, green, blue = (array[..., index].astype(np.int16) for index in range(3))
    magenta = partial & (red > green + 28) & (blue > green + 28)
    return {
        "dimensions": [image.width, image.height],
        "bbox_alpha_gt_8": bbox,
        "padding_px_left_top_right_bottom": [
            bbox[0], bbox[1], image.width - bbox[2], image.height - bbox[3]
        ],
        "alpha_weighted_centroid": [
            round(float((weights * np.arange(alpha.shape[1])[None, :]).sum() / total), 3),
            round(float((weights * np.arange(alpha.shape[0])[:, None]).sum() / total), 3),
        ],
        "transparent_corner_alpha": [
            int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])
        ],
        "partially_transparent_pixels": int(partial.sum()),
        "magenta_dominant_partial_alpha_pixels": int(magenta.sum()),
    }


def build_clean_muzzle(neutral: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Paint out the neutral smile with nearby sampled green muzzle texture."""
    rgb = np.asarray(neutral.convert("RGB"))
    dark = np.zeros((CANVAS[1], CANVAS[0]), dtype=np.uint8)
    x0, y0, x1, y1 = (505, 882, 748, 977)
    roi = rgb[y0:y1, x0:x1]
    # Capture the dark smile and its softer cocoa edge without touching nostrils.
    score = np.max(roi, axis=2)
    dark[y0:y1, x0:x1] = np.where(score < 148, 255, 0).astype(np.uint8)
    mask = Image.fromarray(dark).filter(ImageFilter.MaxFilter(25)).filter(
        ImageFilter.GaussianBlur(6)
    )

    sampled = Image.new("RGB", CANVAS)
    source = neutral.convert("RGB")
    sampled.paste(source.crop((0, 72, CANVAS[0], CANVAS[1])), (0, 0))
    # Only the mouth mask is used, so undefined bottom rows are irrelevant.
    clean_rgb = Image.composite(sampled, source, mask)
    clean = clean_rgb.convert("RGBA")
    clean.putalpha(neutral.getchannel("A"))
    return clean, mask


def shallow_mouth_masks() -> tuple[Image.Image, Image.Image, Image.Image]:
    """Author a smile-connected shallow cavity with a single continuous rim."""
    cavity = Image.new("L", CANVAS, 0)
    draw = ImageDraw.Draw(cavity)
    polygon: list[tuple[int, int]] = []
    for x in range(548, 708):
        d = x - 627.5
        top = int(round(949.0 - 0.00425 * d * d))
        polygon.append((x, top))
    for x in range(707, 547, -1):
        t = (x - 627.5) / 80.0
        d = x - 627.5
        top = 949.0 - 0.00425 * d * d
        depth = 3.0 + 35.0 * max(0.0, 1.0 - t * t)
        polygon.append((x, int(round(top + depth))))
    draw.polygon(polygon, fill=255)
    cavity = cavity.filter(ImageFilter.GaussianBlur(0.65))
    rim = cavity.filter(ImageFilter.MaxFilter(13))
    rim = ImageChops.subtract(rim, cavity).filter(ImageFilter.GaussianBlur(1.1))

    lower = Image.new("L", CANVAS, 0)
    lower_draw = ImageDraw.Draw(lower)
    lower_draw.rectangle((530, 946, 724, 1002), fill=255)
    lower = ImageChops.multiply(rim, lower.filter(ImageFilter.GaussianBlur(4)))
    return cavity, rim, lower


def author_roar_mid(clean: Image.Image) -> tuple[Image.Image, dict[str, Image.Image]]:
    cavity, rim, lower_rim = shallow_mouth_masks()
    clean_rgb = clean.convert("RGB")
    canvas = np.asarray(clean_rgb).copy()
    cavity_array = np.asarray(cavity, dtype=np.float32) / 255.0
    yy = np.arange(CANVAS[1], dtype=np.float32)[:, None]
    # Warm cavity gradient sampled from the accepted generated mouth family.
    gradient = np.clip((yy - 918.0) / 75.0, 0.0, 1.0)[..., None]
    top = np.array([53.0, 20.0, 9.0], dtype=np.float32)
    bottom = np.array([174.0, 68.0, 20.0], dtype=np.float32)
    cavity_rgb = top * (1.0 - gradient) + bottom * gradient
    # Preserve a trace of tactile variation without introducing a separate shape.
    texture = np.asarray(clean_rgb, dtype=np.float32)
    texture_luma = texture.mean(axis=2, keepdims=True) - 145.0
    cavity_rgb = np.clip(cavity_rgb + texture_luma * 0.035, 0, 255)

    rim_array = np.asarray(rim, dtype=np.float32)[..., None] / 255.0
    lower_array = np.asarray(lower_rim, dtype=np.float32)[..., None] / 255.0
    base = canvas.astype(np.float32)
    shadow_rgb = np.array([89.0, 61.0, 13.0], dtype=np.float32)
    base = base * (1.0 - rim_array * 0.42) + shadow_rgb * (rim_array * 0.42)
    light_rgb = np.array([218.0, 239.0, 50.0], dtype=np.float32)
    base = base * (1.0 - lower_array * 0.38) + light_rgb * (lower_array * 0.38)
    cavity_alpha = cavity_array[..., None]
    base = base * (1.0 - cavity_alpha) + cavity_rgb * cavity_alpha
    out = Image.fromarray(np.clip(np.rint(base), 0, 255).astype(np.uint8)).convert("RGBA")
    out.putalpha(clean.getchannel("A"))
    return out, {"cavity": cavity, "rim": rim, "lower-rim": lower_rim}


def repair_roar(
    clean: Image.Image,
    roar_v1: Image.Image,
    smile_mask: Image.Image,
    repair_roi_mask: Image.Image,
) -> tuple[Image.Image, Image.Image]:
    """Remove only the v1 roar's detached side-smile remnants."""
    side = Image.new("L", CANVAS, 0)
    draw = ImageDraw.Draw(side)
    draw.rectangle((492, 874, 570, 979), fill=255)
    draw.rectangle((684, 874, 762, 979), fill=255)
    side = side.filter(ImageFilter.GaussianBlur(4))
    repair_mask = ImageChops.multiply(ImageChops.multiply(smile_mask, side), repair_roi_mask)
    rgb = Image.composite(clean.convert("RGB"), roar_v1.convert("RGB"), repair_mask)
    out = rgb.convert("RGBA")
    out.putalpha(roar_v1.getchannel("A"))
    return out, repair_mask


def main() -> None:
    for directory in (AUDIT, ALPHA, CHROMA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    v1 = {state: rgba(ALPHA / f"{state}-v1.png") for state in STATES}
    neutral = v1["neutral"]
    alpha = neutral.getchannel("A")
    clean, smile_mask = build_clean_muzzle(neutral)
    authored_mid, mouth_masks = author_roar_mid(clean)
    repair_roi_mask = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(repair_roi_mask).rectangle(
        (MOUTH_ROI[0], MOUTH_ROI[1], MOUTH_ROI[2] - 1, MOUTH_ROI[3] - 1), fill=255
    )
    roar_mid = Image.composite(authored_mid, v1["roar-mid"], repair_roi_mask)
    roar, roar_repair_mask = repair_roar(clean, v1["roar"], smile_mask, repair_roi_mask)
    masters = {
        "neutral": v1["neutral"].copy(),
        "blink": v1["blink"].copy(),
        "roar-mid": roar_mid,
        "roar": roar,
    }
    for image in masters.values():
        image.putalpha(alpha)

    smile_mask.save(AUDIT / "v2-neutral-smile-removal-mask.png", optimize=True)
    repair_roi_mask.save(AUDIT / "v2-repair-roi-mask.png", optimize=True)
    roar_repair_mask.save(AUDIT / "v2-roar-side-remnant-repair-mask.png", optimize=True)
    for name, mask in mouth_masks.items():
        mask.save(AUDIT / f"v2-roar-mid-{name}-mask.png", optimize=True)

    runtime: dict[str, Image.Image] = {}
    for state, image in masters.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        image.save(alpha_path, optimize=True)
        keyed = Image.new("RGBA", CANVAS, "#ff00ff")
        keyed.alpha_composite(image)
        keyed.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        image.save(public_path, "WEBP", quality=95, alpha_quality=100, method=6, exact=True)
        if not 200_000 <= public_path.stat().st_size <= 350_000:
            raise RuntimeError(f"{public_path} is outside the 200-350KB runtime band")
        shutil.copy2(public_path, PAGES / public_path.name)
        runtime[state] = rgba(public_path)

    # Actual helper proof at every requested jaw weight, 380px and 96px.
    jaw_weights = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
    mixes = {weight: helper_mix(runtime, weight) for weight in jaw_weights}
    proof_images: list[Image.Image] = []
    proof_labels: list[str] = []
    for weight in jaw_weights:
        at_380 = mixes[weight].resize((380, 380), Image.Resampling.LANCZOS)
        proof_images.append(on_background(at_380, "#233048"))
        proof_labels.append(f"actual helper jaw {weight:.1f} / 380")
    for weight in jaw_weights:
        at_96 = mixes[weight].resize((96, 96), Image.Resampling.LANCZOS)
        proof_images.append(on_background(at_96, "#233048").resize((380, 380), Image.Resampling.NEAREST))
        proof_labels.append(f"actual helper jaw {weight:.1f} / 96 (4x)")
    labeled_sheet(proof_images, proof_labels, 5, 380).save(
        AUDIT / "actual-helper-jaw-380-96-v2.png", optimize=True
    )

    states_380 = [on_background(runtime[state].resize((380, 380), Image.Resampling.LANCZOS), "#eef2f6") for state in STATES]
    labeled_sheet(states_380, [f"{state} / 380" for state in STATES], 4, 380).save(
        AUDIT / "states-380-v2.png", optimize=True
    )
    crop_images: list[Image.Image] = []
    crop_labels: list[str] = []
    for version, images in (("v1", v1), ("v2", masters)):
        for state in ("neutral", "roar-mid", "roar"):
            crop = images[state].crop(MOUTH_ROI).resize((540, 352), Image.Resampling.LANCZOS)
            crop_images.append(on_background(crop, "#233048"))
            crop_labels.append(f"{state} / {version}")
    labeled_sheet(crop_images, crop_labels, 3, 540).save(
        AUDIT / "mouth-repair-v1-v2.png", optimize=True
    )

    hostile_images: list[Image.Image] = []
    hostile_labels: list[str] = []
    for name, background in (("black", "#000000"), ("white", "#ffffff"), ("magenta", "#ff00dc"), ("green", "#00ff00")):
        for state in STATES:
            hostile_images.append(on_background(runtime[state].resize((380, 380), Image.Resampling.LANCZOS), background))
            hostile_labels.append(f"{state} / {name}")
    labeled_sheet(hostile_images, hostile_labels, 4, 380).save(
        AUDIT / "hostile-380-states-v2.png", optimize=True
    )

    # Low-to-high perceptual deltas against the clean muzzle at the actual 380px
    # presentation scale. Gentle low-pass filtering suppresses texture/WebP
    # noise without hiding lighter mouth shapes; secondary components at least
    # 5% of the dominant mouth would still fail the single-component check.
    x0, y0, x1, y1 = MOUTH_ROI
    scale = 380.0 / CANVAS[0]
    roi_380 = tuple(int(round(value * scale)) for value in MOUTH_ROI)
    rx0, ry0, rx1, ry1 = roi_380
    clean_380 = clean.convert("RGB").resize((380, 380), Image.Resampling.LANCZOS).filter(
        ImageFilter.GaussianBlur(1.6)
    )
    clean_rgb = np.asarray(clean_380, dtype=np.float32)
    thresholds = (3, 6, 10, 16, 24)
    component_audit: dict[str, object] = {}
    threshold_images: list[Image.Image] = []
    threshold_labels: list[str] = []
    for weight in jaw_weights:
        mixed_380 = mixes[weight].convert("RGB").resize((380, 380), Image.Resampling.LANCZOS).filter(
            ImageFilter.GaussianBlur(1.6)
        )
        mixed_rgb = np.asarray(mixed_380, dtype=np.float32)
        delta = np.sqrt(np.mean((mixed_rgb - clean_rgb) ** 2, axis=2))[ry0:ry1, rx0:rx1]
        weight_metrics: dict[str, object] = {}
        for threshold in thresholds:
            mask = delta >= threshold
            # One-pixel contact dilation prevents antialiased edges from being
            # misclassified while retaining light isolated remnants.
            mask_image = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
            dilated = np.asarray(mask_image) > 0
            components = connected_components(dilated)
            significance_floor = max(6, int(round(components[0] * 0.05))) if components else 6
            significant = [size for size in components if size >= significance_floor]
            weight_metrics[str(threshold)] = {
                "all_component_sizes": components[:8],
                "significance_floor_pixels": significance_floor,
                "significant_component_sizes": significant,
                "single_significant_component": len(significant) == 1,
            }
            view = Image.new("RGB", (rx1 - rx0, ry1 - ry0), "#101216")
            view.paste((242, 224, 74), mask=mask_image)
            threshold_images.append(view.resize((270, 176), Image.Resampling.NEAREST))
            threshold_labels.append(f"jaw {weight:.1f} / delta >= {threshold}")
        component_audit[f"{weight:.1f}"] = weight_metrics
    labeled_sheet(threshold_images, threshold_labels, 5, 270).save(
        AUDIT / "perceptual-mouth-delta-multithreshold-v2.png", optimize=True
    )

    neutral_array = np.asarray(neutral.convert("RGBA"), dtype=np.int16)
    alpha_hashes = {
        state: hashlib.sha256(image.getchannel("A").tobytes()).hexdigest()
        for state, image in masters.items()
    }
    state_stability: dict[str, object] = {}
    for state, image in masters.items():
        array = np.asarray(image.convert("RGBA"), dtype=np.int16)
        semantic_delta = np.max(np.abs(array[..., :3] - neutral_array[..., :3]), axis=2)
        semantic_changed = semantic_delta > 2
        ys, xs = np.where(semantic_changed)
        v1_array = np.asarray(v1[state].convert("RGBA"), dtype=np.int16)
        repair_delta = np.max(np.abs(array[..., :3] - v1_array[..., :3]), axis=2)
        repaired = repair_delta > 0
        outside = repaired.copy()
        outside[y0:y1, x0:x1] = False
        state_stability[state] = {
            "semantic_changed_pixels_vs_neutral": int(semantic_changed.sum()),
            "semantic_changed_bbox_vs_neutral": None if not len(xs) else [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
            "repair_changed_pixels_vs_same_v1_state": int(repaired.sum()),
            "repair_changed_pixels_outside_mouth_roi": int(outside.sum()),
        }

    manifest: dict[str, object] = {
        "animal": "chameleon",
        "name": "Color-Pop Chameleon",
        "version": VERSION,
        "repair_source": "v1 accepted neutral/blink/roar and v1 locked alpha",
        "repair_method": "deterministic sampled-muzzle texture patch plus authored smile-connected shallow cavity; no new generative call",
        "critic_gap": "neutral-to-roarMid showed a simultaneous smile and separate opening; v1 roar also retained faint side-smile remnants",
        "mouth_roi": list(MOUTH_ROI),
        "runtime_export": {"side_px": 1254, "quality": 95, "alpha_quality": 100, "method": 6},
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "state_stability": state_stability,
        "perceptual_component_audit": component_audit,
        "states": {},
        "evidence": [
            "design/runtime/chameleon/audit/actual-helper-jaw-380-96-v2.png",
            "design/runtime/chameleon/audit/perceptual-mouth-delta-multithreshold-v2.png",
            "design/runtime/chameleon/audit/mouth-repair-v1-v2.png",
            "design/runtime/chameleon/audit/states-380-v2.png",
            "design/runtime/chameleon/audit/hostile-380-states-v2.png",
        ],
    }
    for state, image in masters.items():
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / public_path.name
        manifest["states"][state] = {  # type: ignore[index]
            "runtime_bytes": public_path.stat().st_size,
            "runtime_sha256": sha256(public_path),
            "pages_sha256": sha256(pages_path),
            "parity": sha256(public_path) == sha256(pages_path),
            "contains_alph_chunk": b"ALPH" in public_path.read_bytes(),
            "alpha_metrics": alpha_metrics(image),
        }
    (AUDIT / "manifest-v2.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
