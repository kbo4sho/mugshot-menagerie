from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[4]
BUNNY = ROOT / "design" / "runtime" / "bunny"
CHROMA = BUNNY / "chroma"
ALPHA = BUNNY / "alpha"
AUDIT = BUNNY / "audit"
PUBLIC = ROOT / "public" / "masks" / "bunny"
PAGES = ROOT / "github-pages" / "public" / "masks" / "bunny"
STATES = ("neutral", "blink", "roar")
CANVAS = (1254, 1254)
WEBP_QUALITY = 95


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rounded_mask(
    size: tuple[int, int], boxes: tuple[tuple[int, int, int, int], ...], radius: int, feather: float
) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for box in boxes:
        draw.rounded_rectangle(box, radius=radius, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(feather))


def checker(size: tuple[int, int], cell: int = 24) -> Image.Image:
    width, height = size
    out = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(out)
    for y in range(0, height, cell):
        for x in range(0, width, cell):
            color = "#d8d8d8" if (x // cell + y // cell) % 2 else "#f7f7f7"
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=color)
    return out


def on_background(foreground: Image.Image, background: Image.Image | str) -> Image.Image:
    if isinstance(background, str):
        base = Image.new("RGBA", foreground.size, background)
    else:
        base = background.convert("RGBA")
    return Image.alpha_composite(base, foreground).convert("RGB")


def weighted_blend(a: Image.Image, b: Image.Image, weight: float) -> Image.Image:
    aa = np.asarray(a.convert("RGBA"), dtype=np.float32) / 255.0
    bb = np.asarray(b.convert("RGBA"), dtype=np.float32) / 255.0
    a_alpha = aa[..., 3:4]
    b_alpha = bb[..., 3:4]
    out_alpha = a_alpha * (1.0 - weight) + b_alpha * weight
    out_rgb_p = aa[..., :3] * a_alpha * (1.0 - weight) + bb[..., :3] * b_alpha * weight
    out_rgb = np.divide(out_rgb_p, out_alpha, out=np.zeros_like(out_rgb_p), where=out_alpha > 1e-8)
    return Image.fromarray(
        np.clip(np.concatenate((out_rgb, out_alpha), axis=2) * 255.0 + 0.5, 0, 255).astype(np.uint8)
    )


def clean_partial_green(image: Image.Image) -> tuple[Image.Image, int]:
    pixels = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    red = pixels[..., 0].astype(np.int16)
    green = pixels[..., 1].astype(np.int16)
    blue = pixels[..., 2].astype(np.int16)
    alpha = pixels[..., 3]
    contaminated = (
        (alpha > 0)
        & (alpha < 255)
        & (green > red * 1.15)
        & (green > blue * 1.15)
    )
    pixels[..., 1][contaminated] = np.maximum(red, blue)[contaminated].astype(np.uint8)
    pixels[..., :3][alpha == 0] = 0
    return Image.fromarray(pixels), int(contaminated.sum())


def raised_crown(base: Image.Image, generated: Image.Image) -> Image.Image:
    # The generated P0 repair supplied the correct wider crown. Expand only
    # that crown upward another 28 native pixels for bounce/tilt reserve while
    # preserving the approved v1 ears and face pixel-for-pixel.
    source_box = (400, 438, 854, 660)
    target_box = (400, 410, 854, 660)
    patch = generated.crop(source_box).resize(
        (target_box[2] - target_box[0], target_box[3] - target_box[1]),
        Image.Resampling.LANCZOS,
    )
    layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    layer.paste(patch, target_box[:2])
    crown_window = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(crown_window).rounded_rectangle((425, 382, 829, 674), radius=90, fill=255)
    crown_window = crown_window.filter(ImageFilter.GaussianBlur(8))
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), crown_window))
    return Image.alpha_composite(base.convert("RGBA"), layer)


def geometry_case(
    alpha: np.ndarray,
    angle_degrees: float,
    bounce_asset_px: float,
) -> dict[str, object]:
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

    top_dx = radius_y * sin_t
    top_dy = -radius_y * cos_t
    landmark_x = center_x + top_dx
    landmark_y = center_y + top_dy
    sample_x = int(round(landmark_x))
    sample_y = int(round(landmark_y))
    if alpha[sample_y, sample_x] >= 250:
        edge_y = sample_y
        while edge_y > 0 and alpha[edge_y - 1, sample_x] >= 250:
            edge_y -= 1
        crown_margin = landmark_y - edge_y
    else:
        edge_y = sample_y
        while edge_y < 379 and alpha[edge_y, sample_x] < 250:
            edge_y += 1
        crown_margin = landmark_y - edge_y

    return {
        "angle_degrees": angle_degrees,
        "bounce_asset_px": bounce_asset_px,
        "landmark_10": [landmark_x, landmark_y],
        "opaque_edge_y_at_landmark_x": int(edge_y),
        "crown_margin_px": float(crown_margin),
        "tracked_face_pixels": int(face.sum()),
        "nonopaque_tracked_face_pixels": int(nonopaque.sum()),
        "nonopaque_tracked_face_percent": float(nonopaque.sum() / face.sum() * 100.0),
        "passes_12px_margin": bool(crown_margin >= 12.0),
        "whole_face_opaque": bool(nonopaque.sum() == 0),
    }


def draw_geometry_proof(
    v1: Image.Image,
    v2: Image.Image,
    cases: list[tuple[str, Image.Image, float, float, dict[str, object]]],
) -> Image.Image:
    font = ImageFont.load_default()
    proof = Image.new("RGB", (380 * len(cases), 430), "#161322")
    for col, (label, image, angle, bounce, metrics) in enumerate(cases):
        panel = on_background(image, "#241d35")
        draw = ImageDraw.Draw(panel, "RGBA")
        cx = 190.0
        cy = 227.3 - bounce
        rx = 218.0 / (2.0 * 1.42)
        ry = (310.1 - 144.5) / 2.0
        theta = math.radians(angle)
        points = []
        for index in range(181):
            t = math.tau * index / 180.0
            x = rx * math.cos(t)
            y = ry * math.sin(t)
            points.append(
                (
                    cx + x * math.cos(theta) - y * math.sin(theta),
                    cy + x * math.sin(theta) + y * math.cos(theta),
                )
            )
        passed = bool(metrics["passes_12px_margin"] and metrics["whole_face_opaque"])
        color = (80, 255, 157, 235) if passed else (255, 93, 123, 235)
        draw.line(points + [points[0]], fill=color, width=2)
        lx, ly = metrics["landmark_10"]
        edge_y = metrics["opaque_edge_y_at_landmark_x"]
        draw.line((lx, edge_y, lx, ly), fill=(255, 226, 91, 255), width=2)
        draw.ellipse((lx - 4, ly - 4, lx + 4, ly + 4), fill=(255, 226, 91, 255))
        proof.paste(panel, (col * 380, 0))
        caption = (
            f"{label}  margin {metrics['crown_margin_px']:.1f}px  "
            f"nonopaque {metrics['nonopaque_tracked_face_percent']:.3f}%"
        )
        ImageDraw.Draw(proof).text((col * 380 + 10, 392), caption, fill=color[:3], font=font)
    return proof


def main() -> None:
    raw_generated = AUDIT / "generated-neutral-v2.png"
    extracted_generated = AUDIT / "generated-neutral-extracted-v2.png"
    helper = (
        Path.home()
        / ".codex"
        / "skills"
        / ".system"
        / "imagegen"
        / "scripts"
        / "remove_chroma_key.py"
    )
    subprocess.run(
        [
            sys.executable,
            str(helper),
            "--input",
            str(raw_generated),
            "--out",
            str(extracted_generated),
            "--auto-key",
            "border",
            "--soft-matte",
            "--transparent-threshold",
            "12",
            "--opaque-threshold",
            "220",
            "--despill",
            "--force",
        ],
        check=True,
    )

    v1 = {state: Image.open(ALPHA / f"{state}-v1.png").convert("RGBA") for state in STATES}
    generated = Image.open(extracted_generated).convert("RGBA")
    repaired_neutral = raised_crown(v1["neutral"], generated)
    repaired_neutral, neutral_cleaned = clean_partial_green(repaired_neutral)
    locked_alpha = repaired_neutral.getchannel("A")
    locked_alpha_hash = hashlib.sha256(locked_alpha.tobytes()).hexdigest()
    safe_interior = locked_alpha.filter(ImageFilter.MinFilter(41))

    blink_mask = rounded_mask(
        CANVAS,
        ((278, 728, 570, 1018), (684, 728, 976, 1018)),
        radius=115,
        feather=18,
    )
    roar_mask = rounded_mask(
        CANVAS,
        ((505, 941, 749, 1184), (350, 630, 515, 760), (739, 630, 904, 760)),
        radius=54,
        feather=16,
    )
    state_masks = {
        "blink": ImageChops.multiply(blink_mask, safe_interior),
        "roar": ImageChops.multiply(roar_mask, safe_interior),
    }

    images: dict[str, Image.Image] = {"neutral": repaired_neutral}
    cleaned_pixels = {"neutral": neutral_cleaned}
    for state, mask in state_masks.items():
        rgb = Image.composite(v1[state].convert("RGB"), repaired_neutral.convert("RGB"), mask)
        image = rgb.convert("RGBA")
        image.putalpha(locked_alpha)
        image, count = clean_partial_green(image)
        image.putalpha(locked_alpha)
        images[state] = image
        cleaned_pixels[state] = count

    for state, image in images.items():
        image.putalpha(locked_alpha)
        image.save(ALPHA / f"{state}-v2.png", optimize=True)
        chroma = Image.new("RGBA", CANVAS, "#00ff00")
        chroma.alpha_composite(image)
        chroma.convert("RGB").save(CHROMA / f"{state}-v2.png", optimize=True)

    exports: dict[str, dict[str, object]] = {}
    runtime_images: dict[str, Image.Image] = {}
    for state, image in images.items():
        target = PUBLIC / f"{state}-v2.webp"
        image.save(
            target,
            "WEBP",
            quality=WEBP_QUALITY,
            alpha_quality=100,
            method=6,
            exact=True,
        )
        pages_target = PAGES / target.name
        pages_target.write_bytes(target.read_bytes())
        decoded = Image.open(target).convert("RGBA")
        runtime_images[state] = decoded
        decoded_alpha_hash = hashlib.sha256(decoded.getchannel("A").tobytes()).hexdigest()
        exports[state] = {
            "public_path": str(target.relative_to(ROOT)),
            "pages_path": str(pages_target.relative_to(ROOT)),
            "bytes": target.stat().st_size,
            "sha256": sha256(target),
            "pages_sha256": sha256(pages_target),
            "pages_byte_equal": target.read_bytes() == pages_target.read_bytes(),
            "has_alph_chunk": b"ALPH" in target.read_bytes(),
            "decoded_alpha_sha256": decoded_alpha_hash,
            "decoded_alpha_matches_master": decoded_alpha_hash == locked_alpha_hash,
        }

    small = {
        state: image.resize((380, 380), Image.Resampling.LANCZOS)
        for state, image in runtime_images.items()
    }
    backgrounds: list[Image.Image | str] = [
        "#ffffff",
        "#101018",
        "#00ff00",
        "#ff00ff",
        "#00ffff",
        checker((380, 380)),
    ]
    hostile = Image.new("RGB", (380 * 3, 380 * len(backgrounds)), "#777777")
    for row, background in enumerate(backgrounds):
        for col, state in enumerate(STATES):
            hostile.paste(on_background(small[state], background), (col * 380, row * 380))
    hostile.save(AUDIT / "hostile-380-states-v2.png", optimize=True)

    native = Image.new("RGB", (CANVAS[0] * 3, CANVAS[1]), "#101018")
    for col, state in enumerate(STATES):
        native.paste(on_background(images[state], checker(CANVAS, cell=48)), (col * CANVAS[0], 0))
    native.save(AUDIT / "native-states-v2.jpg", quality=92, optimize=True)

    weights = (0.0, 0.25, 0.5, 0.75, 1.0)
    crossfade = Image.new("RGB", (380 * len(weights), 380 * 2), "#17171f")
    for row, state in enumerate(("blink", "roar")):
        for col, weight in enumerate(weights):
            blend = weighted_blend(runtime_images["neutral"], runtime_images[state], weight).resize(
                (380, 380), Image.Resampling.LANCZOS
            )
            crossfade.paste(on_background(blend, checker((380, 380))), (col * 380, row * 380))
    crossfade.save(AUDIT / "copy-lighter-crossfades-380-v2.png", optimize=True)

    v1_runtime = Image.open(PUBLIC / "neutral-v1.webp").convert("RGBA").resize(
        (380, 380), Image.Resampling.LANCZOS
    )
    v2_runtime = small["neutral"]
    v1_alpha_380 = np.asarray(v1_runtime.getchannel("A"))
    v2_alpha_380 = np.asarray(v2_runtime.getchannel("A"))
    geometry = {
        "v1_static": geometry_case(v1_alpha_380, 0.0, 0.0),
        "v2_static": geometry_case(v2_alpha_380, 0.0, 0.0),
        "v2_tilt_left_bounce": geometry_case(v2_alpha_380, -8.0, 3.5),
        "v2_tilt_right_bounce": geometry_case(v2_alpha_380, 8.0, 3.5),
    }
    proof_cases = [
        ("v1 static", v1_runtime, 0.0, 0.0, geometry["v1_static"]),
        ("v2 static", v2_runtime, 0.0, 0.0, geometry["v2_static"]),
        (
            "v2 -8deg + bounce",
            v2_runtime,
            -8.0,
            3.5,
            geometry["v2_tilt_left_bounce"],
        ),
        (
            "v2 +8deg + bounce",
            v2_runtime,
            8.0,
            3.5,
            geometry["v2_tilt_right_bounce"],
        ),
    ]
    draw_geometry_proof(v1_runtime, v2_runtime, proof_cases).save(
        AUDIT / "canonical-landmark-geometry-v2.png", optimize=True
    )

    alpha_array = np.asarray(locked_alpha)
    ys, xs = np.where(alpha_array > 0)
    neutral_rgb = np.asarray(images["neutral"].convert("RGB"), dtype=np.int16)
    partial = (alpha_array > 0) & (alpha_array < 255)
    green_fringe = partial & (neutral_rgb[..., 1] > neutral_rgb[..., 0] * 1.15) & (
        neutral_rgb[..., 1] > neutral_rgb[..., 2] * 1.15
    )
    centerline_opaque = np.where(alpha_array[:, CANVAS[0] // 2] >= 250)[0]
    ear_tip_padding_380 = ys.min() * 380.0 / CANVAS[1]

    metrics = {
        "version": "v2",
        "native_dimensions": list(CANVAS),
        "runtime_dimensions": list(CANVAS),
        "review_dimensions": [380, 380],
        "webp_quality": WEBP_QUALITY,
        "repair": "targeted generated crown transplanted over exact v1, then crown expanded upward 28px",
        "alpha_bbox": [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)],
        "alpha_centroid": [float(xs.mean()), float(ys.mean())],
        "padding_px": {
            "left": int(xs.min()),
            "top": int(ys.min()),
            "right": int(CANVAS[0] - 1 - xs.max()),
            "bottom": int(CANVAS[1] - 1 - ys.max()),
        },
        "ear_tip_padding_380_px": float(ear_tip_padding_380),
        "centerline_opaque_head_top_native_y": int(centerline_opaque.min()),
        "centerline_opaque_head_top_380_y": float(centerline_opaque.min() * 380.0 / CANVAS[1]),
        "corner_alpha": [
            int(alpha_array[0, 0]),
            int(alpha_array[0, -1]),
            int(alpha_array[-1, 0]),
            int(alpha_array[-1, -1]),
        ],
        "alpha_sha256": locked_alpha_hash,
        "partial_alpha_pixels": int(partial.sum()),
        "partial_alpha_green_fringe_pixels_after_cleanup": int(green_fringe.sum()),
        "partial_alpha_green_pixels_cleaned_by_state": cleaned_pixels,
        "geometry": geometry,
        "exports": exports,
    }
    (AUDIT / "manifest-v2.json").write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
