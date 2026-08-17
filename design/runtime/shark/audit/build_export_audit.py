#!/usr/bin/env python3
"""Localize, extract, export, and audit Silly Shark v1."""

from __future__ import annotations

import hashlib
import io
import json
import math
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[4]
ANIMAL = ROOT / "design/runtime/shark"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
AUDIT = ANIMAL / "audit"
PUBLIC = ROOT / "public/masks/shark"
PAGES = ROOT / "github-pages/public/masks/shark"
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


def checker(size: tuple[int, int], cell: int = 24) -> Image.Image:
    out = Image.new("RGBA", size, (247, 247, 247, 255))
    draw = ImageDraw.Draw(out)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(205, 209, 219, 255))
    return out


def composite_over(
    image: Image.Image,
    background: Image.Image | tuple[int, int, int],
    side: int = 380,
) -> Image.Image:
    fitted = image.convert("RGBA").resize((side, side), Image.Resampling.LANCZOS)
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
    sheet = Image.new("RGB", (columns * cell, rows * (cell + header)), (25, 26, 34))
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


def canonical_geometry_case(
    alpha: np.ndarray, angle_degrees: float, bounce_asset_px: float
) -> dict[str, object]:
    """Measure coverage of the app's canonical tracked-face ellipse at 380 px."""
    center_x = 190.0
    center_y = 227.3 - bounce_asset_px
    radius_x = 218.0 / (2.0 * 1.42)
    radius_y = (310.1 - 144.5) / 2.0
    theta = math.radians(angle_degrees)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    yy, xx = np.mgrid[0:380, 0:380]
    dx = xx - center_x
    dy = yy - center_y
    local_x = cos_t * dx + sin_t * dy
    local_y = -sin_t * dx + cos_t * dy
    face = (local_x / radius_x) ** 2 + (local_y / radius_y) ** 2 <= 1.0
    nonopaque = face & (alpha < 250)
    landmark_x = center_x + radius_y * sin_t
    landmark_y = center_y - radius_y * cos_t
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


def draw_canonical_geometry_proof(
    image: Image.Image, cases: list[tuple[str, dict[str, object]]]
) -> Image.Image:
    proof = Image.new("RGB", (380 * len(cases), 430), "#161322")
    font = ImageFont.load_default()
    foreground = image.convert("RGBA").resize((380, 380), Image.Resampling.LANCZOS)
    for column, (label, metrics) in enumerate(cases):
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
            points.append(
                (
                    center_x + x * math.cos(theta) - y * math.sin(theta),
                    center_y + x * math.sin(theta) + y * math.cos(theta),
                )
            )
        passed = bool(metrics["passes_12px_margin"] and metrics["whole_face_opaque"])
        color = (80, 255, 157, 235) if passed else (255, 93, 123, 235)
        draw.line(points + [points[0]], fill=color, width=2)
        landmark_x, landmark_y = metrics["landmark_10"]
        edge_y = metrics["opaque_edge_y_at_landmark_x"]
        draw.line((landmark_x, edge_y, landmark_x, landmark_y), fill=(255, 226, 91, 255), width=2)
        draw.ellipse(
            (landmark_x - 4, landmark_y - 4, landmark_x + 4, landmark_y + 4),
            fill=(255, 226, 91, 255),
        )
        proof.paste(panel.convert("RGB"), (column * 380, 0))
        caption = (
            f"{label}  margin {metrics['crown_margin_px']:.1f}px  "
            f"nonopaque {metrics['nonopaque_tracked_face_percent']:.3f}%"
        )
        ImageDraw.Draw(proof).text((column * 380 + 10, 392), caption, fill=color[:3], font=font)
    return proof


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
                queue.append((y, x))
                outside[y, x] = True
    for y in range(height):
        for x in (0, width - 1):
            if transparent[y, x] and not outside[y, x]:
                queue.append((y, x))
                outside[y, x] = True
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
    return {
        "dimensions": [image.width, image.height],
        "bbox_alpha_gt_8": bbox,
        "padding_px_left_top_right_bottom": [bbox[0], bbox[1], width - bbox[2], height - bbox[3]],
        "alpha_weighted_centroid": [round(value, 3) for value in centroid],
        "centerline_opaque_span_y": [int(centerline.min()), int(centerline.max())] if centerline.size else None,
        "transparent_corner_alpha": [int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])],
        "partially_transparent_pixels": int(partial.sum()),
        "enclosed_fully_transparent_hole_pixels": int((transparent & ~outside).sum()),
        "green_dominant_partial_alpha_pixels": int(green_fringe.sum()),
    }


def webp_bytes(image: Image.Image, side: int, quality: int) -> bytes:
    runtime = image if image.size == (side, side) else image.resize((side, side), Image.Resampling.LANCZOS)
    stream = io.BytesIO()
    runtime.save(stream, "WEBP", quality=quality, alpha_quality=100, method=6, exact=True)
    return stream.getvalue()


def main() -> None:
    for directory in (CHROMA, ALPHA, AUDIT, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    source_paths: dict[str, Path] = {}
    for state in STATES:
        source = AUDIT / f"{state}-generated-{VERSION}.png"
        if not source.exists():
            shutil.copy2(CHROMA / f"{state}-{VERSION}.png", source)
        source_paths[state] = source

    raw = {state: Image.open(path).convert("RGB") for state, path in source_paths.items()}
    if len({image.size for image in raw.values()}) != 1:
        raise RuntimeError("Generated state dimensions differ")
    size = raw["neutral"].size

    extracted_path = AUDIT / f"neutral-extracted-{VERSION}.png"
    helper = Path.home() / ".codex/skills/.system/imagegen/scripts/remove_chroma_key.py"
    subprocess.run(
        [
            sys.executable,
            str(helper),
            "--input", str(source_paths["neutral"]),
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

    # Localized RGB edits preserve the neutral silhouette, gills, cheeks, skin,
    # color, and matte byte-for-byte outside the intended expression regions.
    blink_mask = feathered_mask(
        size,
        [
            ("ellipse", (175, 370, 565, 825), 0),
            ("ellipse", (689, 370, 1079, 825), 0),
        ],
        14,
    )
    roar_mask = feathered_mask(
        size,
        [
            ("rounded", (190, 375, 500, 565), 68),
            ("rounded", (754, 375, 1064, 565), 68),
            ("ellipse", (430, 830, 824, 1120), 0),
        ],
        15,
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
    candidate_blobs: dict[tuple[int, int], dict[str, bytes]] = {}
    for side in (1254, 1152, 1024):
        for quality in (95, 94):
            blobs = {state: webp_bytes(image, side, quality) for state, image in states.items()}
            candidate_blobs[(side, quality)] = blobs
            sizes = [len(blobs[state]) for state in STATES]
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
    chosen_blobs = candidate_blobs[(chosen_side, chosen_quality)]
    for state in STATES:
        target = PUBLIC / f"{state}-{VERSION}.webp"
        target.write_bytes(chosen_blobs[state])
        shutil.copy2(target, PAGES / target.name)
        runtime_states[state] = Image.open(target).convert("RGBA")

    native_images: list[Image.Image] = []
    native_labels: list[str] = []
    for state in STATES:
        native_images.append(composite_over(runtime_states[state], checker((380, 380)), 380))
        native_labels.append(f"{state} / runtime 380px")
    for state in STATES:
        tiny = composite_over(runtime_states[state], (232, 237, 244), 96)
        native_images.append(tiny.resize((380, 380), Image.Resampling.NEAREST))
        native_labels.append(f"{state} / runtime 96px (4x)")
    labeled_sheet(native_images, native_labels, 3).save(AUDIT / f"states-380-and-96-{VERSION}.png")

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

    runtime_380 = {
        state: image.resize((380, 380), Image.Resampling.LANCZOS)
        for state, image in runtime_states.items()
    }
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
        mixes.append(composite_over(copy_lighter_mix(runtime_380, blink, roar), (17, 22, 36), 380))
        mix_labels.append(label)
    labeled_sheet(mixes, mix_labels, 5).save(AUDIT / f"copy-lighter-crossfades-380-{VERSION}.png")

    neutral_alpha_380 = np.asarray(runtime_380["neutral"].getchannel("A"))
    canonical_geometry = {
        "static": canonical_geometry_case(neutral_alpha_380, 0.0, 0.0),
        "tilt_left_bounce": canonical_geometry_case(neutral_alpha_380, -8.0, 3.5),
        "tilt_right_bounce": canonical_geometry_case(neutral_alpha_380, 8.0, 3.5),
    }
    draw_canonical_geometry_proof(
        runtime_states["neutral"],
        [
            ("static", canonical_geometry["static"]),
            ("-8deg + bounce", canonical_geometry["tilt_left_bounce"]),
            ("+8deg + bounce", canonical_geometry["tilt_right_bounce"]),
        ],
    ).save(AUDIT / f"canonical-forehead-geometry-{VERSION}.png")

    alpha_hashes = {
        state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
        for state, image in states.items()
    }
    decoded_alpha_hashes = {
        state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
        for state, image in runtime_states.items()
    }
    neutral_array = np.asarray(states["neutral"], dtype=np.int16)
    manifest: dict[str, object] = {
        "animal": "shark",
        "name": "Silly Shark",
        "version": VERSION,
        "generation_route": "built-in ImageGen neutral using Bumblebee v1 solely as finish/composition reference; blink and roar edits used shark neutral as sole target; state RGB localized onto neutral",
        "provenance": "design/runtime/shark/audit/provenance-v1.md",
        "targeted_retries": {"neutral": 0, "blink": 0, "roar": 0},
        "manual_visual_assertions_for_independent_review": {
            "species": "front-facing blue-gray shark head; attached dorsal crown cue; three gill slits per side; blunt snout; no body, tail, water, or detached fins",
            "neutral": "gentle closed smile and zero teeth",
            "blink": "two happy closed arcs and closed smile",
            "roar": "compact centered O mouth, warm tongue, exactly two small rounded upper teeth; no row or fangs",
            "safety": "joyful, non-aggressive, child-safe in all three states",
        },
        "localization": {
            "shared_alpha": True,
            "blink_scope": "eye and brow regions only",
            "roar_scope": "mouth and brow regions only",
            "outside_localization_max_channel_delta": {
                state: int(
                    np.abs(np.asarray(states[state], dtype=np.int16) - neutral_array)[np.asarray(masks[state]) == 0].max()
                )
                for state in ("blink", "roar")
            },
        },
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
        "runtime_decoded_alpha_pixel_hashes": decoded_alpha_hashes,
        "runtime_decoded_alpha_pixel_hashes_identical": len(set(decoded_alpha_hashes.values())) == 1,
        "canonical_geometry": canonical_geometry,
        "states": {},
    }
    for state, image in states.items():
        source_path = source_paths[state]
        chroma_path = CHROMA / f"{state}-{VERSION}.png"
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        runtime_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / runtime_path.name
        manifest["states"][state] = {
            "generated_chroma_source": str(source_path.relative_to(ROOT)),
            "generated_source_sha256": sha256(source_path),
            "localized_chroma_master": str(chroma_path.relative_to(ROOT)),
            "localized_chroma_sha256": sha256(chroma_path),
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "runtime": str(runtime_path.relative_to(ROOT)),
            "runtime_bytes": runtime_path.stat().st_size,
            "runtime_sha256": sha256(runtime_path),
            "github_pages_sha256": sha256(pages_path),
            "runtime_copies_identical": runtime_path.read_bytes() == pages_path.read_bytes(),
            "has_alph_chunk": b"ALPH" in runtime_path.read_bytes(),
            "metrics": alpha_metrics(image),
        }
    (AUDIT / f"manifest-{VERSION}.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
