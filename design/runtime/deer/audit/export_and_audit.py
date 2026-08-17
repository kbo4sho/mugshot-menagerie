#!/usr/bin/env python3
"""Localize, harmonize, export, and audit Dapper Deer v1."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[4]
DEER = ROOT / "design/runtime/deer"
AUDIT = DEER / "audit"
ALPHA = DEER / "alpha"
CHROMA = DEER / "chroma"
PUBLIC = ROOT / "public/masks/deer"
PAGES = ROOT / "github-pages/public/masks/deer"
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


def exact_green_chroma(image: Image.Image) -> Image.Image:
    field = Image.new("RGBA", image.size, (0, 255, 0, 255))
    field.alpha_composite(image)
    return field.convert("RGB")


def repair_isolated_alpha_holes(
    image: Image.Image, max_component_pixels: int = 16
) -> tuple[Image.Image, int]:
    """Fill only tiny transparent islands fully enclosed by the subject."""
    array = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    transparent = array[..., 3] == 0
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
    visited = np.zeros_like(holes, dtype=bool)
    repaired = 0
    for start_y, start_x in np.argwhere(holes):
        if visited[start_y, start_x]:
            continue
        component: list[tuple[int, int]] = []
        component_queue = deque([(int(start_y), int(start_x))])
        visited[start_y, start_x] = True
        while component_queue:
            y, x = component_queue.popleft()
            component.append((y, x))
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if (
                    0 <= ny < height
                    and 0 <= nx < width
                    and holes[ny, nx]
                    and not visited[ny, nx]
                ):
                    visited[ny, nx] = True
                    component_queue.append((ny, nx))
        if len(component) > max_component_pixels:
            continue
        neighbors: list[np.ndarray] = []
        for y, x in component:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if (
                        0 <= ny < height
                        and 0 <= nx < width
                        and array[ny, nx, 3] > 0
                    ):
                        neighbors.append(array[ny, nx])
        if not neighbors:
            continue
        samples = np.stack(neighbors)
        rgb = np.median(samples[:, :3], axis=0).astype(np.uint8)
        alpha = int(samples[:, 3].max())
        for y, x in component:
            array[y, x, :3] = rgb
            array[y, x, 3] = alpha
            repaired += 1
    return Image.fromarray(array), repaired


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
    foreground = fit_square(image, 380)
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
        ImageDraw.Draw(proof).text(
            (column * 380 + 10, 392), caption, fill=color[:3], font=font
        )
    return proof


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

    neutral, repaired_holes = repair_isolated_alpha_holes(
        rgba(AUDIT / "neutral-extracted-v1.png")
    )
    blink_source = rgba(AUDIT / "blink-extracted-v1.png")
    roar_source = rgba(AUDIT / "roar-extracted-v1.png")
    size = neutral.size

    # Replace only the complete neutral eye islands with the bilateral happy arcs.
    # Protected cheek ovals prevent regenerated blush entering the state.
    blink_mask = expression_mask(
        size,
        [(286, 615, 599, 932), (655, 615, 968, 932)],
        blur=14,
        protected=[(274, 867, 409, 1004), (845, 867, 980, 1004)],
    )
    # The roar borrows only the compact O mouth and subtle brow lifts.
    roar_mask = expression_mask(
        size,
        [(545, 918, 709, 1090), (338, 506, 471, 616), (783, 506, 916, 616)],
        blur=13,
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
    runtime_alpha_hashes = {
        state: hashlib.sha256(runtime_states[state].getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }

    neutral_380 = fit_square(runtime_states["neutral"], 380)
    neutral_alpha_380 = np.asarray(neutral_380.getchannel("A"))
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
    ).save(AUDIT / "canonical-forehead-geometry-v1.png")

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

    # Edge closeups: left antler and crown over hostile backgrounds.
    edge_images: list[Image.Image] = []
    edge_labels: list[str] = []
    for name, background in (
        ("black", (0, 0, 0)),
        ("white", (255, 255, 255)),
        ("cyan", (0, 220, 255)),
        ("magenta", (255, 0, 220)),
    ):
        composed = composite_over(runtime_states["neutral"], background, chosen_side)
        crop = composed.crop((270, 105, 560, 470)).resize((380, 380), Image.Resampling.NEAREST)
        edge_images.append(crop)
        edge_labels.append(f"left antler edge / {name}")
    contact_sheet(edge_images, 4, edge_labels).save(AUDIT / "antler-edge-closeups-v1.png")

    alpha_hashes = {
        state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
        for state, image in states.items()
    }
    neutral_array = np.asarray(states["neutral"], dtype=np.int16)
    blink_outside = np.asarray(blink_mask) == 0
    roar_outside = np.asarray(roar_mask) == 0
    manifest: dict[str, object] = {
        "animal": "deer",
        "name": "Dapper Deer",
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
        "runtime_decoded_alpha_pixel_hashes": runtime_alpha_hashes,
        "runtime_decoded_alpha_pixel_hashes_identical": len(set(runtime_alpha_hashes.values())) == 1,
        "localization_mask_nonzero_pixels": {
            "blink": int((np.asarray(blink_mask) > 0).sum()),
            "roar": int((np.asarray(roar_mask) > 0).sum()),
        },
        "neutral_enclosed_alpha_hole_pixels_repaired": repaired_holes,
        "canonical_forehead_geometry_380": canonical_geometry,
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
            "imagegen_source": str((AUDIT / "imagegen" / f"{state}-{VERSION}.generated.png").relative_to(ROOT)),
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
