#!/usr/bin/env python3
"""Repair Sloth transition geometry non-destructively as v3."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from build_export_audit import (
    CANVAS,
    ROOT,
    STATES,
    alpha_metrics,
    copy_lighter_mix,
    labeled_sheet,
    on_background,
    rgba,
    sha256,
)
from build_export_audit_v2 import components, save_ramp, tongue_free_cavity


ANIMAL = ROOT / "design/runtime/sloth"
AUDIT = ANIMAL / "audit"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
PUBLIC = ROOT / "public/masks/sloth"
PAGES = ROOT / "github-pages/public/masks/sloth"
VERSION = "v3"
SHIFT_UP_NATIVE_PX = 16
PROOF_WEIGHTS = (0.0, 0.10, 0.25, 0.50, 0.75, 1.0)
PERCEPTUAL_THRESHOLDS = (105, 115, 125, 135, 145, 155, 165)
PROBE_ROI = (168, 255, 212, 289)


def opening_hierarchy(source: Image.Image) -> tuple[Image.Image, int]:
    """Make the upper bridge emerge before the warm lower cavity.

    Low-weight linear blends cannot darken bright muzzle pixels immediately.
    A deep upper cavity plus a continuously lighter lower cavity prevents the
    lower O from crossing perceptual thresholds before its connecting bridge.
    """
    array = np.asarray(source.convert("RGB"), dtype=np.uint8).copy()
    red, green, blue = array[..., 0], array[..., 1], array[..., 2]
    yy, xx = np.mgrid[0 : array.shape[0], 0 : array.shape[1]]
    candidate = (
        (xx >= 548)
        & (xx < 704)
        & (yy >= 806)
        & (yy < 974)
        & (red < 225)
        & (green < 170)
        & (blue < 125)
    )
    seed = (862, 626)
    if not candidate[seed]:
        raise RuntimeError("Sloth v3 shifted-mouth seed is outside its cavity")
    connected = np.zeros_like(candidate, dtype=bool)
    queue: deque[tuple[int, int]] = deque([seed])
    connected[seed] = True
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if (
                0 <= ny < candidate.shape[0]
                and 0 <= nx < candidate.shape[1]
                and candidate[ny, nx]
                and not connected[ny, nx]
            ):
                connected[ny, nx] = True
                queue.append((ny, nx))

    # Stay nearly black through the bridge, then smoothly rise into one muted
    # cocoa lower interior. There is no discrete tongue boundary or island.
    raw_t = np.clip((yy.astype(np.float32) - 894.0) / 48.0, 0.0, 1.0)
    t = raw_t * raw_t * (3.0 - 2.0 * raw_t)
    texture = (
        np.sin(xx.astype(np.float32) * 0.169)
        + np.sin(yy.astype(np.float32) * 0.131)
    ) * 1.8
    top = np.array([8.0, 4.0, 2.0], dtype=np.float32)
    bottom = np.array([150.0, 105.0, 72.0], dtype=np.float32)
    target = top[None, None, :] * (1.0 - t[..., None]) + bottom[None, None, :] * t[..., None]
    target += texture[..., None]
    blend_mask = Image.fromarray(connected.astype(np.uint8) * 255)
    blend_mask = blend_mask.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(2))
    mix = np.asarray(blend_mask, dtype=np.float32)[..., None] / 255.0
    blended = array.astype(np.float32) * (1.0 - mix) + target * mix
    return Image.fromarray(np.clip(np.rint(blended), 0, 255).astype(np.uint8)), int(connected.sum())


def shifted_mouth_source(raw_source: Image.Image) -> tuple[Image.Image, int]:
    """Move the complete generated mouth/muzzle patch upward 16 native pixels.

    The v2 O began below the neutral smile. Sampling the whole local patch from
    16 pixels lower moves its upper cavity rim onto the neutral smile's central
    span while also replacing the old mouth location with lower muzzle texture.
    """
    harmonized, cavity_pixels = tongue_free_cavity(raw_source)
    shifted = harmonized.copy()
    target_box = (500, 800, 754, 1028)
    source_box = (
        target_box[0],
        target_box[1] + SHIFT_UP_NATIVE_PX,
        target_box[2],
        target_box[3] + SHIFT_UP_NATIVE_PX,
    )
    shifted.paste(harmonized.crop(source_box), target_box[:2])
    shifted, hierarchy_pixels = opening_hierarchy(shifted)
    return shifted, max(cavity_pixels, hierarchy_pixels)


def v3_localization_mask(alpha: Image.Image) -> Image.Image:
    mask = Image.new("L", CANVAS, 0)
    draw = ImageDraw.Draw(mask)
    # Wide upper lobe repaints the entire old smile; the lower lobe contains
    # the translated O. Their large overlap prevents a muzzle-colored gap.
    draw.ellipse((500, 795, 754, 928), fill=255)
    draw.ellipse((535, 790, 719, 1002), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(13))
    safe_interior = alpha.filter(ImageFilter.MinFilter(41))
    return ImageChops.multiply(mask, safe_interior)


def perceptual_luminance(rgb: np.ndarray) -> np.ndarray:
    return (
        rgb[..., 0].astype(np.float32) * 0.2126
        + rgb[..., 1].astype(np.float32) * 0.7152
        + rgb[..., 2].astype(np.float32) * 0.0722
    )


def largest_horizontal_run(binary: np.ndarray) -> int:
    best = 0
    for row in binary:
        current = 0
        for value in row:
            current = current + 1 if value else 0
            best = max(best, current)
    return best


def component_profile(image: Image.Image) -> dict[str, object]:
    # Tight mouth-only crop: excludes nose, cheek blush, and chin fur.
    x0, y0, x1, y1 = PROBE_ROI
    rgb = np.asarray(image.convert("RGB"))[y0:y1, x0:x1]
    luminance = perceptual_luminance(rgb)
    profiles: dict[str, object] = {}
    for threshold in PERCEPTUAL_THRESHOLDS:
        binary = luminance < threshold
        significant = [component for component in components(binary) if int(component["area"]) >= 64]
        profiles[str(threshold)] = {
            "significant_component_count": len(significant),
            "components": significant[:4],
            "visible_pixels": int(binary.sum()),
            "largest_horizontal_run_top_16px": largest_horizontal_run(binary[:16]),
            "single_component_spans_opening": bool(
                len(significant) == 1
                and int(significant[0]["bbox_xyxy"][1]) <= 12
                and int(significant[0]["bbox_xyxy"][3]) >= 18
            ),
        }
    return {"roi_xyxy": [x0, y0, x1, y1], "thresholds": profiles}


def main() -> None:
    for directory in (AUDIT, CHROMA, ALPHA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    neutral = rgba(ALPHA / "neutral-v1.png")
    blink = rgba(ALPHA / "blink-v1.png")
    raw_source_path = AUDIT / "generated-roar-v2.png"
    raw_source = Image.open(raw_source_path).convert("RGB")
    shifted_source, harmonized_cavity_pixels = shifted_mouth_source(raw_source)
    shifted_source_path = AUDIT / "generated-roar-geometry-v3.png"
    shifted_source.save(shifted_source_path, optimize=True)

    neutral_alpha = neutral.getchannel("A")
    mouth_mask = v3_localization_mask(neutral_alpha)
    mouth_mask.save(AUDIT / "roar-localization-mask-v3.png")
    roar_rgb = Image.composite(shifted_source, neutral.convert("RGB"), mouth_mask)
    roar = roar_rgb.convert("RGBA")
    roar.putalpha(neutral_alpha)
    masters = {"neutral": neutral, "blink": blink, "roar": roar}

    for state, image in masters.items():
        image.putalpha(neutral_alpha)
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        chroma = Image.new("RGBA", CANVAS, "#00ff00")
        chroma.alpha_composite(image)
        chroma.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    candidates: dict[tuple[int, int], list[int]] = {}
    chosen_side: int | None = None
    chosen_quality: int | None = None
    for side in (1254, 1152, 1024, 960, 896):
        for quality in (95, 94):
            sizes: list[int] = []
            for state, image in masters.items():
                runtime = image if side == 1254 else image.resize((side, side), Image.Resampling.LANCZOS)
                candidate = AUDIT / f"candidate-{state}-{side}-q{quality}-v3.webp"
                runtime.save(
                    candidate,
                    "WEBP",
                    quality=quality,
                    alpha_quality=100,
                    method=6,
                    exact=True,
                )
                sizes.append(candidate.stat().st_size)
            candidates[(side, quality)] = sizes
            if min(sizes) >= 200_000 and max(sizes) <= 350_000:
                chosen_side, chosen_quality = side, quality
                break
        if chosen_side is not None:
            break
    if chosen_side is None or chosen_quality is None:
        raise RuntimeError(f"No q94-95 Sloth v3 export met 200-350KB: {candidates}")

    runtime_images: dict[str, Image.Image] = {}
    for state, image in masters.items():
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
        runtime_images[state] = rgba(public_path)

    actual_380 = {
        state: runtime_images[state].resize((380, 380), Image.Resampling.LANCZOS)
        for state in STATES
    }
    actual_96 = {
        state: runtime_images[state].resize((96, 96), Image.Resampling.LANCZOS)
        for state in STATES
    }

    weight_profiles: dict[str, object] = {}
    stills_380: list[Image.Image] = []
    stills_96: list[Image.Image] = []
    labels: list[str] = []
    for weight in PROOF_WEIGHTS:
        mixed_380 = copy_lighter_mix(actual_380, 0.0, weight)
        mixed_96 = copy_lighter_mix(actual_96, 0.0, weight)
        label = f"roar {int(weight * 100)}%"
        labels.append(label)
        stills_380.append(on_background(mixed_380, "#233048"))
        stills_96.append(
            on_background(mixed_96, "#233048").resize((380, 380), Image.Resampling.NEAREST)
        )
        weight_profiles[f"{weight:.2f}"] = component_profile(mixed_380)
    labeled_sheet(stills_380, labels, 3, 380).save(AUDIT / "production-roar-weights-380-v3.png")
    labeled_sheet(stills_96, [f"{label} / 96px 4x" for label in labels], 3, 380).save(
        AUDIT / "production-roar-weights-96-v3.png"
    )

    # Visualize the exact perceptual probe at thresholds that exposed v2's
    # separate bar/oval components. White pixels are under the threshold.
    threshold_images: list[Image.Image] = []
    threshold_labels: list[str] = []
    probe_x0, probe_y0, probe_x1, probe_y1 = PROBE_ROI
    for weight in (0.10, 0.25, 0.50, 0.75):
        mixed = copy_lighter_mix(actual_380, 0.0, weight)
        crop = np.asarray(mixed.convert("RGB"))[probe_y0:probe_y1, probe_x0:probe_x1]
        luminance = perceptual_luminance(crop)
        for threshold in (125, 145, 155, 165):
            binary = (luminance < threshold).astype(np.uint8) * 255
            preview = Image.fromarray(binary).convert("RGB").resize(
                (380, 380), Image.Resampling.NEAREST
            )
            threshold_images.append(preview)
            threshold_labels.append(f"roar {int(weight * 100)}% / L*<{threshold}")
    labeled_sheet(threshold_images, threshold_labels, 4, 380).save(
        AUDIT / "perceptual-component-thresholds-v3.png"
    )

    ramp_metrics_380 = save_ramp(actual_380, 380, AUDIT / "production-roar-ramp-936ms-380-v3.gif")
    ramp_metrics_96 = save_ramp(actual_380, 96, AUDIT / "production-roar-ramp-936ms-96-v3.gif")

    native = [on_background(masters[state], "#edf0f5") for state in STATES]
    labeled_sheet(native, [f"{state} / native v3" for state in STATES], 3, CANVAS[0]).save(
        AUDIT / "native-states-v3.jpg", quality=92, optimize=True
    )
    hostile: list[Image.Image] = []
    hostile_labels: list[str] = []
    for background_name, background in (
        ("white", "#ffffff"),
        ("black", "#000000"),
        ("cyan", "#00dcff"),
        ("magenta", "#ff00dc"),
    ):
        for state in STATES:
            hostile.append(on_background(actual_380[state], background))
            hostile_labels.append(f"{state} / {background_name}")
    labeled_sheet(hostile, hostile_labels, 3, 380).save(AUDIT / "hostile-380-states-v3.png")

    comparison: list[Image.Image] = []
    comparison_labels: list[str] = []
    for version in ("v1", "v2", "v3"):
        states = (
            actual_380
            if version == "v3"
            else {
                state: rgba(PUBLIC / f"{state}-{version}.webp").resize(
                    (380, 380), Image.Resampling.LANCZOS
                )
                for state in STATES
            }
        )
        for weight in (0.10, 0.25, 0.50, 0.75):
            comparison.append(on_background(copy_lighter_mix(states, 0.0, weight), "#233048"))
            comparison_labels.append(f"{version} / roar {int(weight * 100)}%")
    labeled_sheet(comparison, comparison_labels, 4, 380).save(
        AUDIT / "v1-v2-v3-roar-compare-380.png"
    )

    requested_weights = (0.10, 0.25, 0.50, 0.75)
    connected_all = True
    for weight in requested_weights:
        thresholds = weight_profiles[f"{weight:.2f}"]["thresholds"]
        for threshold in PERCEPTUAL_THRESHOLDS:
            count = int(thresholds[str(threshold)]["significant_component_count"])
            if count != 1:
                connected_all = False

    alpha_hashes = {
        state: hashlib.sha256(masters[state].getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }
    neutral_array = np.asarray(neutral, dtype=np.int16)
    outside = np.asarray(mouth_mask) == 0
    manifest: dict[str, object] = {
        "animal": "sloth",
        "name": "Sleepy Sloth",
        "version": VERSION,
        "repair_scope": "roar target geometry only; v1/v2 retained; accepted identity, neutral, blink, alpha, silhouette, and matte preserved",
        "generation_route": "deterministic v3 from the existing generated v2 source; no new ImageGen call",
        "geometry_repair": {
            "mouth_patch_shift_up_native_px": SHIFT_UP_NATIVE_PX,
            "harmonized_connected_cavity_pixels": harmonized_cavity_pixels,
            "source": str(raw_source_path.relative_to(ROOT)),
            "derived_source": str(shifted_source_path.relative_to(ROOT)),
        },
        "runtime_export": {
            "side_px": chosen_side,
            "quality": chosen_quality,
            "alpha_quality": 100,
            "method": 6,
        },
        "candidate_sizes_bytes": {
            f"{side}-q{quality}": values
            for (side, quality), values in candidates.items()
        },
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "neutral_v1_v3_file_sha256_equal": sha256(ALPHA / "neutral-v1.png") == sha256(ALPHA / "neutral-v3.png"),
        "blink_v1_v3_file_sha256_equal": sha256(ALPHA / "blink-v1.png") == sha256(ALPHA / "blink-v3.png"),
        "roar_outside_localization_max_channel_delta": int(
            np.abs(np.asarray(roar, dtype=np.int16) - neutral_array)[outside].max()
        ),
        "perceptual_component_probe": {
            "thresholds": list(PERCEPTUAL_THRESHOLDS),
            "minimum_significant_component_area_px": 64,
            "all_requested_weights_single_component_at_all_thresholds": connected_all,
            "weights": weight_profiles,
        },
        "gallery_ramp": {
            "production_source_duration_ms": 936,
            "sampled_frames": 24,
            "encoded_gif_duration_ms": 960,
            "metrics_380": ramp_metrics_380,
            "metrics_96": ramp_metrics_96,
        },
        "states": {},
    }
    for state, image in masters.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        chroma_path = CHROMA / f"{state}-{VERSION}.png"
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / public_path.name
        manifest["states"][state] = {
            "chroma_master": str(chroma_path.relative_to(ROOT)),
            "chroma_sha256": sha256(chroma_path),
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "runtime": str(public_path.relative_to(ROOT)),
            "runtime_bytes": public_path.stat().st_size,
            "runtime_sha256": sha256(public_path),
            "github_pages_sha256": sha256(pages_path),
            "runtime_copies_identical": sha256(public_path) == sha256(pages_path),
            "metrics": alpha_metrics(image),
        }
    (AUDIT / "manifest-v3.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
