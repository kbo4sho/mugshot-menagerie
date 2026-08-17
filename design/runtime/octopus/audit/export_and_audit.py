#!/usr/bin/env python3
"""Localize, export, and audit the Bubbly Octopus v1 rendered-state pack."""

from __future__ import annotations

import hashlib
import io
import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[4]
ANIMAL = ROOT / "design/runtime/octopus"
ALPHA = ANIMAL / "alpha"
CHROMA = ANIMAL / "chroma"
AUDIT = ANIMAL / "audit"
PUBLIC = ROOT / "public/masks/octopus"
PAGES = ROOT / "github-pages/public/masks/octopus"
STATES = ("neutral", "blink", "roar")
VERSION = "v1"
CANVAS = (1254, 1254)


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ellipse_mask(boxes: list[tuple[int, int, int, int]], blur: int) -> Image.Image:
    mask = Image.new("L", CANVAS, 0)
    draw = ImageDraw.Draw(mask)
    for box in boxes:
        draw.ellipse(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def localize(neutral: Image.Image, source: Image.Image, mask: Image.Image) -> Image.Image:
    rgb = Image.composite(source.convert("RGB"), neutral.convert("RGB"), mask)
    out = rgb.convert("RGBA")
    out.putalpha(neutral.getchannel("A"))
    return out


def exact_green_chroma(image: Image.Image) -> Image.Image:
    field = Image.new("RGBA", CANVAS, (0, 255, 0, 255))
    field.alpha_composite(image)
    return field.convert("RGB")


def webp_bytes(image: Image.Image, side: int, quality: int) -> bytes:
    if side != image.width:
        image = image.resize((side, side), Image.Resampling.LANCZOS)
    stream = io.BytesIO()
    image.save(
        stream,
        "WEBP",
        quality=quality,
        alpha_quality=100,
        method=6,
        exact=True,
    )
    return stream.getvalue()


def premultiplied_blend(images: list[Image.Image], weights: list[float]) -> Image.Image:
    arrays = [np.asarray(image.convert("RGBA"), dtype=np.float32) / 255.0 for image in images]
    alpha = sum(weight * array[..., 3:4] for weight, array in zip(weights, arrays))
    rgbp = sum(weight * array[..., :3] * array[..., 3:4] for weight, array in zip(weights, arrays))
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    merged = np.concatenate([rgb, alpha], axis=2)
    return Image.fromarray(np.clip(np.rint(merged * 255), 0, 255).astype(np.uint8), "RGBA")


def fit(image: Image.Image, side: int) -> Image.Image:
    thumb = image.copy()
    thumb.thumbnail((side, side), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(thumb, ((side - thumb.width) // 2, (side - thumb.height) // 2))
    return canvas


def composite(image: Image.Image, background: tuple[int, int, int], side: int) -> Image.Image:
    panel = Image.new("RGBA", (side, side), background + (255,))
    panel.alpha_composite(fit(image, side))
    return panel.convert("RGB")


def contact_sheet(
    images: list[Image.Image], labels: list[str], columns: int, cell: int
) -> Image.Image:
    font = ImageFont.load_default()
    label_h = 24
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell, rows * (cell + label_h)), "#202028")
    draw = ImageDraw.Draw(sheet)
    for index, (image, label) in enumerate(zip(images, labels)):
        x = (index % columns) * cell
        y = (index // columns) * (cell + label_h)
        tile = image.convert("RGB")
        if tile.size != (cell, cell):
            tile = tile.resize((cell, cell), Image.Resampling.LANCZOS)
        sheet.paste(tile, (x, y))
        draw.text((x + 6, y + cell + 6), label, fill="white", font=font)
    return sheet


def alpha_metrics(image: Image.Image) -> dict[str, object]:
    array = np.asarray(image.convert("RGBA"))
    alpha = array[..., 3]
    ys, xs = np.where(alpha > 8)
    partial = (alpha > 0) & (alpha < 255)
    fringe = partial & (array[..., 1] > array[..., 0] * 1.25) & (array[..., 1] > array[..., 2] * 1.25)
    opaque = alpha >= 250
    transparent_map = Image.fromarray(((alpha == 0) * 255).astype(np.uint8), "L").copy()
    ImageDraw.floodfill(transparent_map, (0, 0), 128, thresh=0)
    enclosed_transparent_holes = int((np.asarray(transparent_map) == 255).sum())
    weights = alpha.astype(np.float64)
    total = max(weights.sum(), 1)
    centroid = [
        float((weights * np.arange(alpha.shape[1])[None, :]).sum() / total),
        float((weights * np.arange(alpha.shape[0])[:, None]).sum() / total),
    ]
    return {
        "bbox_alpha_gt_8": [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)],
        "padding_ltrb": [int(xs.min()), int(ys.min()), int(image.width - xs.max() - 1), int(image.height - ys.max() - 1)],
        "alpha_weighted_centroid": [round(value, 3) for value in centroid],
        "transparent_corner_alpha": [int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])],
        "opaque_pixels": int((alpha == 255).sum()),
        "partial_alpha_pixels": int(partial.sum()),
        "green_dominant_partial_alpha_pixels": int(fringe.sum()),
        "enclosed_fully_transparent_hole_pixels": enclosed_transparent_holes,
        "nearly_opaque_center_ellipse_fraction": round(float(opaque[300:900, 300:954].mean()), 6),
    }


def chroma_metrics(chroma: Image.Image, alpha_master: Image.Image) -> dict[str, object]:
    rgb = np.asarray(chroma.convert("RGB"))
    alpha = np.asarray(alpha_master.getchannel("A"))
    exterior = alpha == 0
    exact_green = np.all(rgb == np.array([0, 255, 0], dtype=np.uint8), axis=2)
    return {
        "exterior_pixels": int(exterior.sum()),
        "exterior_exact_green_pixels": int((exterior & exact_green).sum()),
        "exterior_exact_green_fraction": round(float(exact_green[exterior].mean()), 8),
    }


def max_outside_delta(neutral: Image.Image, state: Image.Image, mask: Image.Image) -> int:
    a = np.asarray(neutral.convert("RGB"), dtype=np.int16)
    b = np.asarray(state.convert("RGB"), dtype=np.int16)
    outside = np.asarray(mask) == 0
    return int(np.abs(a - b)[outside].max(initial=0))


def canonical_geometry_case(
    alpha: np.ndarray, angle_degrees: float, bounce_asset_px: float
) -> dict[str, object]:
    """Measure coverage of the app's canonical tracked-face ellipse at 380 px."""
    center_x = 190.0
    center_y = 227.3 - bounce_asset_px
    radius_x = 218.0 / (2.0 * 1.42)
    radius_y = (310.1 - 144.5) / 2.0
    theta = math.radians(angle_degrees)
    yy, xx = np.mgrid[0:380, 0:380]
    dx = xx - center_x
    dy = yy - center_y
    local_x = math.cos(theta) * dx + math.sin(theta) * dy
    local_y = -math.sin(theta) * dx + math.cos(theta) * dy
    face = (local_x / radius_x) ** 2 + (local_y / radius_y) ** 2 <= 1.0
    nonopaque = face & (alpha < 250)
    landmark_x = center_x + radius_y * math.sin(theta)
    landmark_y = center_y - radius_y * math.cos(theta)
    sample_x = int(round(landmark_x))
    sample_y = int(round(landmark_y))
    edge_y = sample_y
    if alpha[sample_y, sample_x] >= 250:
        while edge_y > 0 and alpha[edge_y - 1, sample_x] >= 250:
            edge_y -= 1
    else:
        while edge_y < 379 and alpha[edge_y, sample_x] < 250:
            edge_y += 1
    crown_margin = landmark_y - edge_y
    return {
        "angle_degrees": angle_degrees,
        "bounce_asset_px": bounce_asset_px,
        "landmark_10": [round(landmark_x, 3), round(landmark_y, 3)],
        "opaque_edge_y_at_landmark_x": int(edge_y),
        "crown_margin_px": round(float(crown_margin), 3),
        "tracked_face_pixels": int(face.sum()),
        "nonopaque_tracked_face_pixels": int(nonopaque.sum()),
        "nonopaque_tracked_face_percent": round(float(nonopaque.sum() / face.sum() * 100), 6),
        "passes_12px_margin": bool(crown_margin >= 12.0),
        "whole_face_opaque": bool(nonopaque.sum() == 0),
    }


def canonical_proof(image: Image.Image, cases: dict[str, dict[str, object]]) -> Image.Image:
    proof = Image.new("RGB", (380 * len(cases), 430), "#161322")
    font = ImageFont.load_default()
    foreground = fit(image, 380)
    for column, (label, metrics) in enumerate(cases.items()):
        panel = Image.new("RGBA", (380, 380), (36, 29, 53, 255))
        panel.alpha_composite(foreground)
        draw = ImageDraw.Draw(panel, "RGBA")
        center_x = 190.0
        center_y = 227.3 - float(metrics["bounce_asset_px"])
        radius_x = 218.0 / (2.0 * 1.42)
        radius_y = (310.1 - 144.5) / 2.0
        theta = math.radians(float(metrics["angle_degrees"]))
        points = []
        for index in range(181):
            t = math.tau * index / 180.0
            x = radius_x * math.cos(t)
            y = radius_y * math.sin(t)
            points.append((center_x + x * math.cos(theta) - y * math.sin(theta), center_y + x * math.sin(theta) + y * math.cos(theta)))
        passed = bool(metrics["passes_12px_margin"] and metrics["whole_face_opaque"])
        color = (80, 255, 157, 235) if passed else (255, 93, 123, 235)
        draw.line(points + [points[0]], fill=color, width=2)
        landmark_x, landmark_y = metrics["landmark_10"]
        edge_y = metrics["opaque_edge_y_at_landmark_x"]
        draw.line((landmark_x, edge_y, landmark_x, landmark_y), fill=(255, 226, 91, 255), width=2)
        proof.paste(panel.convert("RGB"), (column * 380, 0))
        caption = f"{label}  margin {metrics['crown_margin_px']:.1f}px  nonopaque {metrics['nonopaque_tracked_face_percent']:.3f}%"
        ImageDraw.Draw(proof).text((column * 380 + 10, 392), caption, fill=color[:3], font=font)
    return proof


def build() -> None:
    for directory in (ALPHA, CHROMA, AUDIT, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    neutral = rgba(ALPHA / "neutral-raw-v1.png")
    blink_source = rgba(ALPHA / "blink-raw-v1.png")
    roar_source = rgba(ALPHA / "roar-raw-v1.png")

    # Eyes plus surrounding lids; large enough to fully replace the generated open-eye islands.
    blink_mask = ellipse_mask([(275, 430, 575, 760), (675, 430, 975, 760)], 18)
    # One compact mouth island plus two eyebrow islands. Tentacle and cheek pixels stay neutral.
    roar_mask = ellipse_mask(
        [(530, 635, 720, 855), (315, 325, 520, 465), (735, 325, 940, 465)], 14
    )
    blink_mask.save(AUDIT / "blink-localization-mask-v1.png")
    roar_mask.save(AUDIT / "roar-localization-mask-v1.png")

    states = {
        "neutral": neutral,
        "blink": localize(neutral, blink_source, blink_mask),
        "roar": localize(neutral, roar_source, roar_mask),
    }
    for state, image in states.items():
        image.save(ALPHA / f"{state}-v1.png", optimize=True)
        exact_green_chroma(image).save(CHROMA / f"{state}-v1.png", optimize=True)

    candidates: list[tuple[int, int, dict[str, bytes]]] = []
    for side in (1254, 1152, 1024):
        for quality in (95, 94):
            blobs = {state: webp_bytes(image, side, quality) for state, image in states.items()}
            sizes = [len(blob) for blob in blobs.values()]
            if max(sizes) <= 350_000 and min(sizes) >= 200_000:
                candidates.append((side, quality, blobs))
    if candidates:
        selected_side, selected_quality, blobs = max(candidates, key=lambda item: (item[0], item[1]))
    else:
        # Preserve the largest compliant export even when texture complexity falls below the soft minimum.
        all_candidates = []
        for side in (1254, 1152, 1024):
            for quality in (95, 94):
                blobs = {state: webp_bytes(image, side, quality) for state, image in states.items()}
                if max(map(len, blobs.values())) <= 350_000:
                    all_candidates.append((side, quality, blobs))
        if not all_candidates:
            raise RuntimeError("No q94-95 candidate is below 350 KB per state")
        selected_side, selected_quality, blobs = max(all_candidates, key=lambda item: (item[0], item[1]))

    for state, blob in blobs.items():
        public_path = PUBLIC / f"{state}-v1.webp"
        public_path.write_bytes(blob)
        shutil.copy2(public_path, PAGES / f"{state}-v1.webp")

    runtime = {state: rgba(PUBLIC / f"{state}-v1.webp") for state in STATES}
    runtime_380 = {state: fit(image, 380) for state, image in runtime.items()}
    neutral_alpha_380 = np.asarray(runtime_380["neutral"].getchannel("A"))
    canonical_geometry = {
        "static": canonical_geometry_case(neutral_alpha_380, 0.0, 0.0),
        "tilt_left_bounce": canonical_geometry_case(neutral_alpha_380, -8.0, 3.5),
        "tilt_right_bounce": canonical_geometry_case(neutral_alpha_380, 8.0, 3.5),
    }
    canonical_proof(runtime["neutral"], canonical_geometry).save(AUDIT / "canonical-forehead-geometry-v1.png")

    previews: list[Image.Image] = []
    labels: list[str] = []
    for side in (380, 96):
        for state in STATES:
            previews.append(composite(runtime[state], (244, 240, 232), side).resize((380, 380), Image.Resampling.NEAREST if side == 96 else Image.Resampling.LANCZOS))
            labels.append(f"{state} / {side}px")
    contact_sheet(previews, labels, 3, 380).save(AUDIT / "states-native-96-380-v1.png")

    blends: list[Image.Image] = []
    blend_labels: list[str] = []
    for target in ("blink", "roar"):
        for weight in (0.0, 0.25, 0.5, 0.75, 1.0):
            blend = premultiplied_blend([runtime_380["neutral"], runtime_380[target]], [1.0 - weight, weight])
            blends.append(composite(blend, (242, 240, 234), 380))
            blend_labels.append(f"neutral->{target} {weight:.2f}")
    contact_sheet(blends, blend_labels, 5, 380).save(AUDIT / "copy-lighter-crossfades-380-v1.png")

    hostile: list[Image.Image] = []
    hostile_labels: list[str] = []
    backgrounds = {
        "white": (255, 255, 255),
        "black": (0, 0, 0),
        "green": (0, 255, 0),
        "magenta": (255, 0, 255),
    }
    for name, color in backgrounds.items():
        for state in STATES:
            hostile.append(composite(runtime[state], color, 380))
            hostile_labels.append(f"{state} / {name}")
    contact_sheet(hostile, hostile_labels, 3, 380).save(AUDIT / "hostile-380-states-v1.png")

    # Close crops of curled tips/suction cups over dark and light fields.
    closeups: list[Image.Image] = []
    closeup_labels: list[str] = []
    for state in STATES:
        crop = runtime[state].crop((0, int(runtime[state].height * 0.52), runtime[state].width, runtime[state].height))
        for name, color in (("black", (0, 0, 0)), ("white", (255, 255, 255))):
            closeups.append(composite(crop, color, 380))
            closeup_labels.append(f"tentacle matte / {state} / {name}")
    contact_sheet(closeups, closeup_labels, 3, 380).save(AUDIT / "tentacle-matte-closeups-v1.png")

    alpha_hashes = {
        state: hashlib.sha256(rgba(ALPHA / f"{state}-v1.png").getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }
    runtime_alpha_hashes = {
        state: hashlib.sha256(runtime[state].getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }
    manifest = {
        "animal": "octopus",
        "display_name": "Bubbly Octopus",
        "version": VERSION,
        "generation_route": "built-in ImageGen neutral using Bumblebee v1 only as finish/composition reference; blink and roar generated from Octopus neutral as sole edit target; one targeted roar retry removed a tongue",
        "localization": {
            "shared_neutral_alpha": True,
            "blink_scope": "bilateral eye islands",
            "roar_scope": "one compact mouth island plus two brow islands",
            "outside_localization_max_rgb_delta": {
                "blink": max_outside_delta(states["neutral"], states["blink"], blink_mask),
                "roar": max_outside_delta(states["neutral"], states["roar"], roar_mask),
            },
        },
        "runtime_export": {
            "dimensions": [selected_side, selected_side],
            "quality": selected_quality,
            "alpha_quality": 100,
            "method": 6,
            "target_bytes_per_state": [200_000, 350_000],
            "sizes": {state: len(blobs[state]) for state in STATES},
        },
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "runtime_decoded_alpha_pixel_hashes": runtime_alpha_hashes,
        "runtime_decoded_alpha_pixel_hashes_identical": len(set(runtime_alpha_hashes.values())) == 1,
        "canonical_geometry": canonical_geometry,
        "states": {},
    }
    for state in STATES:
        alpha_path = ALPHA / f"{state}-v1.png"
        chroma_path = CHROMA / f"{state}-v1.png"
        public_path = PUBLIC / f"{state}-v1.webp"
        pages_path = PAGES / f"{state}-v1.webp"
        manifest["states"][state] = {
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "chroma_master": str(chroma_path.relative_to(ROOT)),
            "chroma_sha256": sha256(chroma_path),
            "public_runtime": str(public_path.relative_to(ROOT)),
            "public_sha256": sha256(public_path),
            "pages_runtime": str(pages_path.relative_to(ROOT)),
            "pages_sha256": sha256(pages_path),
            "public_pages_byte_identical": public_path.read_bytes() == pages_path.read_bytes(),
            "metrics": alpha_metrics(rgba(alpha_path)),
            "chroma_metrics": chroma_metrics(Image.open(chroma_path), rgba(alpha_path)),
        }
    (AUDIT / "metrics-v1.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    build()
