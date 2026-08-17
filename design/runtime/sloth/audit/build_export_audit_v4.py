#!/usr/bin/env python3
"""Build Sloth v4 directly from the accepted v1 baseline."""

from __future__ import annotations

import hashlib
import json
import shutil
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
from build_export_audit_v2 import components, save_ramp


ANIMAL = ROOT / "design/runtime/sloth"
AUDIT = ANIMAL / "audit"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
PUBLIC = ROOT / "public/masks/sloth"
PAGES = ROOT / "github-pages/public/masks/sloth"
VERSION = "v4"
PROOF_WEIGHTS = (0.0, 0.10, 0.25, 0.50, 0.75, 1.0)
DELTA_E_THRESHOLDS = (1.0, 2.0, 3.0, 5.0, 8.0, 12.0)
LUMINANCE_THRESHOLDS = (90, 105, 120, 135, 150, 165)
MOUTH_ROI = (170, 255, 210, 292)


def luminance(rgb: np.ndarray) -> np.ndarray:
    return (
        rgb[..., 0].astype(np.float32) * 0.2126
        + rgb[..., 1].astype(np.float32) * 0.7152
        + rgb[..., 2].astype(np.float32) * 0.0722
    )


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    srgb = rgb.astype(np.float32) / 255.0
    linear = np.where(
        srgb <= 0.04045,
        srgb / 12.92,
        ((srgb + 0.055) / 1.055) ** 2.4,
    )
    x = linear[..., 0] * 0.4124564 + linear[..., 1] * 0.3575761 + linear[..., 2] * 0.1804375
    y = linear[..., 0] * 0.2126729 + linear[..., 1] * 0.7151522 + linear[..., 2] * 0.0721750
    z = linear[..., 0] * 0.0193339 + linear[..., 1] * 0.1191920 + linear[..., 2] * 0.9503041
    xyz = np.stack((x / 0.95047, y / 1.0, z / 1.08883), axis=2)
    delta = 6.0 / 29.0
    f = np.where(xyz > delta**3, np.cbrt(xyz), xyz / (3 * delta**2) + 4.0 / 29.0)
    return np.stack((116.0 * f[..., 1] - 16.0, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])), axis=2)


def delta_e76(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.sqrt(np.square(srgb_to_lab(a) - srgb_to_lab(b)).sum(axis=2))


def build_roar_target(neutral: Image.Image) -> tuple[Image.Image, Image.Image, Image.Image, Image.Image]:
    neutral_rgb = neutral.convert("RGB")
    array = np.asarray(neutral_rgb, dtype=np.uint8)
    lum = luminance(array)

    # Detect only the original smile below the fixed cream nose band. The nose
    # is excluded by y>=850. Dilate slightly to cover the smile's antialiasing.
    smile_binary = np.zeros(CANVAS[::-1], dtype=np.uint8)
    smile_binary[850:880, 515:740] = (lum[850:880, 515:740] < 142).astype(np.uint8) * 255
    smile_mask = Image.fromarray(smile_binary).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(2))

    # Sample real cream muzzle texture from 30 pixels below each smile pixel.
    sampled = array.copy()
    sampled[:-30] = array[30:]
    sampled_image = Image.fromarray(sampled)
    target = Image.composite(sampled_image, neutral_rgb, smile_mask)

    # One near-uniform dark-cocoa ellipse. Its top begins at native y=858,
    # directly on the central neutral smile, while the cream band above remains
    # untouched. A 1.5px feather keeps the rendered edge premium without a lobe.
    hard_cavity = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(hard_cavity).ellipse((574, 858, 680, 958), fill=255)
    cavity_mask = hard_cavity.filter(ImageFilter.GaussianBlur(1.5))
    yy, xx = np.mgrid[0 : CANVAS[1], 0 : CANVAS[0]]
    texture = (np.sin(xx * 0.151) + np.sin(yy * 0.137)) * 1.4
    cocoa = np.empty((CANVAS[1], CANVAS[0], 3), dtype=np.float32)
    cocoa[..., 0] = 58.0 + texture
    cocoa[..., 1] = 28.0 + texture * 0.35
    cocoa[..., 2] = 18.0 + texture * 0.25
    cocoa_image = Image.fromarray(np.clip(np.rint(cocoa), 0, 255).astype(np.uint8))
    target = Image.composite(cocoa_image, target, cavity_mask)

    edit_mask = ImageChops.lighter(smile_mask, cavity_mask)
    return target, smile_mask, cavity_mask, hard_cavity


def significant(binary: np.ndarray, minimum: int = 8) -> list[dict[str, object]]:
    return [component for component in components(binary) if int(component["area"]) >= minimum]


def cream_gap_metrics(image: Image.Image) -> dict[str, object]:
    rgb = np.asarray(image.convert("RGB"))
    lum = luminance(rgb)
    # Median center-line darkness separates nose and mouth; count the bright
    # compositor rows between the final dark pixel of the nose and first mouth.
    center = np.median(lum[220:300, 184:197], axis=1)
    dark_rows = np.where(center < 105)[0] + 220
    groups: list[list[int]] = []
    for row in dark_rows:
        if not groups or row > groups[-1][-1] + 1:
            groups.append([int(row)])
        else:
            groups[-1].append(int(row))
    meaningful = [group for group in groups if len(group) >= 2]
    gap = None
    if len(meaningful) >= 2:
        gap = meaningful[1][0] - meaningful[0][-1] - 1
    strip = rgb[252:258, 184:197]
    return {
        "center_dark_row_groups": [[group[0], group[-1]] for group in meaningful],
        "cream_rows_between_nose_and_mouth": gap,
        "fixed_strip_roi_xyxy": [184, 252, 197, 258],
        "fixed_strip_min_luminance": round(float(luminance(strip).min()), 4),
        "fixed_strip_mean_luminance": round(float(luminance(strip).mean()), 4),
    }


def topology_metrics(
    image: Image.Image,
    neutral: Image.Image,
    hard_cavity_380: np.ndarray,
) -> dict[str, object]:
    rgb = np.asarray(image.convert("RGB"))
    neutral_rgb = np.asarray(neutral.convert("RGB"))
    x0, y0, x1, y1 = MOUTH_ROI
    roi = rgb[y0:y1, x0:x1]
    neutral_roi = neutral_rgb[y0:y1, x0:x1]
    cavity = hard_cavity_380[y0:y1, x0:x1]
    delta = delta_e76(roi, neutral_roi)
    neutral_lum = luminance(neutral_roi)
    current_lum = luminance(roi)
    # The central neutral smile is the opening anchor. DeltaE-visible cavity
    # pixels must join it instead of forming a lower island.
    anchor = (neutral_lum < 125) & (np.indices(neutral_lum.shape)[0] < 13)
    delta_profiles: dict[str, object] = {}
    for threshold in DELTA_E_THRESHOLDS:
        visible = (delta >= threshold) & cavity
        joined = visible | anchor
        found = significant(joined, minimum=6)
        delta_profiles[f"{threshold:.1f}"] = {
            "visible_cavity_pixels": int(visible.sum()),
            "joined_significant_component_count": len(found),
            "components": found[:3],
        }
    luminance_profiles: dict[str, object] = {}
    for threshold in LUMINANCE_THRESHOLDS:
        binary = current_lum < threshold
        found = significant(binary, minimum=8)
        luminance_profiles[str(threshold)] = {
            "significant_component_count": len(found),
            "components": found[:3],
        }
    return {
        "roi_xyxy": list(MOUTH_ROI),
        "delta_e76": delta_profiles,
        "perceptual_luminance": luminance_profiles,
        "cream_gap": cream_gap_metrics(image),
    }


def main() -> None:
    for directory in (AUDIT, CHROMA, ALPHA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    neutral = rgba(ALPHA / "neutral-v1.png")
    blink = rgba(ALPHA / "blink-v1.png")
    roar_target_rgb, smile_mask, cavity_mask, hard_cavity = build_roar_target(neutral)
    smile_mask.save(AUDIT / "smile-erase-mask-v4.png")
    cavity_mask.save(AUDIT / "uniform-cavity-mask-v4.png")
    hard_cavity.save(AUDIT / "uniform-cavity-hard-mask-v4.png")
    edit_mask = ImageChops.lighter(smile_mask, cavity_mask)
    edit_mask.save(AUDIT / "roar-localization-mask-v4.png")
    roar_target_path = AUDIT / "deterministic-roar-target-v4.png"
    roar_target_rgb.save(roar_target_path, optimize=True)

    neutral_alpha = neutral.getchannel("A")
    roar = roar_target_rgb.convert("RGBA")
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
                candidate = AUDIT / f"candidate-{state}-{side}-q{quality}-v4.webp"
                runtime.save(candidate, "WEBP", quality=quality, alpha_quality=100, method=6, exact=True)
                sizes.append(candidate.stat().st_size)
            candidates[(side, quality)] = sizes
            if min(sizes) >= 200_000 and max(sizes) <= 350_000:
                chosen_side, chosen_quality = side, quality
                break
        if chosen_side is not None:
            break
    if chosen_side is None or chosen_quality is None:
        raise RuntimeError(f"No q94-95 Sloth v4 export met 200-350KB: {candidates}")

    runtime_images: dict[str, Image.Image] = {}
    for state, image in masters.items():
        runtime = image if chosen_side == 1254 else image.resize((chosen_side, chosen_side), Image.Resampling.LANCZOS)
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        runtime.save(public_path, "WEBP", quality=chosen_quality, alpha_quality=100, method=6, exact=True)
        shutil.copy2(public_path, PAGES / public_path.name)
        runtime_images[state] = rgba(public_path)

    actual_380 = {state: runtime_images[state].resize((380, 380), Image.Resampling.LANCZOS) for state in STATES}
    actual_96 = {state: runtime_images[state].resize((96, 96), Image.Resampling.LANCZOS) for state in STATES}
    hard_cavity_380 = np.asarray(hard_cavity.resize((380, 380), Image.Resampling.LANCZOS)) > 32

    stills_380: list[Image.Image] = []
    stills_96: list[Image.Image] = []
    labels: list[str] = []
    weight_metrics: dict[str, object] = {}
    for weight in PROOF_WEIGHTS:
        mixed_380 = copy_lighter_mix(actual_380, 0.0, weight)
        mixed_96 = copy_lighter_mix(actual_96, 0.0, weight)
        label = f"roar {int(weight * 100)}%"
        labels.append(label)
        stills_380.append(on_background(mixed_380, "#233048"))
        stills_96.append(on_background(mixed_96, "#233048").resize((380, 380), Image.Resampling.NEAREST))
        weight_metrics[f"{weight:.2f}"] = topology_metrics(
            mixed_380, actual_380["neutral"], hard_cavity_380
        )
    labeled_sheet(stills_380, labels, 3, 380).save(AUDIT / "production-roar-weights-380-v4.png")
    labeled_sheet(stills_96, [f"{label} / 96px 4x" for label in labels], 3, 380).save(
        AUDIT / "production-roar-weights-96-v4.png"
    )

    # DeltaE+anchor topology proof: white is the existing central smile plus
    # cavity pixels whose perceptual change clears the labeled DeltaE threshold.
    de_images: list[Image.Image] = []
    de_labels: list[str] = []
    x0, y0, x1, y1 = MOUTH_ROI
    neutral_roi = np.asarray(actual_380["neutral"].convert("RGB"))[y0:y1, x0:x1]
    neutral_lum = luminance(neutral_roi)
    anchor = (neutral_lum < 125) & (np.indices(neutral_lum.shape)[0] < 13)
    cavity_roi = hard_cavity_380[y0:y1, x0:x1]
    for weight in (0.10, 0.25, 0.50, 0.75):
        mixed = copy_lighter_mix(actual_380, 0.0, weight)
        roi = np.asarray(mixed.convert("RGB"))[y0:y1, x0:x1]
        de = delta_e76(roi, neutral_roi)
        for threshold in (2.0, 3.0, 5.0, 8.0):
            binary = ((de >= threshold) & cavity_roi) | anchor
            preview = Image.fromarray(binary.astype(np.uint8) * 255).convert("RGB").resize(
                (380, 380), Image.Resampling.NEAREST
            )
            de_images.append(preview)
            de_labels.append(f"roar {int(weight * 100)}% / DeltaE≥{int(threshold)}")
    labeled_sheet(de_images, de_labels, 4, 380).save(AUDIT / "delta-e-mouth-topology-v4.png")

    ramp_metrics_380 = save_ramp(actual_380, 380, AUDIT / "production-roar-ramp-936ms-380-v4.gif")
    ramp_metrics_96 = save_ramp(actual_380, 96, AUDIT / "production-roar-ramp-936ms-96-v4.gif")

    native = [on_background(masters[state], "#edf0f5") for state in STATES]
    labeled_sheet(native, [f"{state} / native v4" for state in STATES], 3, CANVAS[0]).save(
        AUDIT / "native-states-v4.jpg", quality=92, optimize=True
    )
    hostile: list[Image.Image] = []
    hostile_labels: list[str] = []
    for background_name, background in (("white", "#ffffff"), ("black", "#000000"), ("cyan", "#00dcff"), ("magenta", "#ff00dc")):
        for state in STATES:
            hostile.append(on_background(actual_380[state], background))
            hostile_labels.append(f"{state} / {background_name}")
    labeled_sheet(hostile, hostile_labels, 3, 380).save(AUDIT / "hostile-380-states-v4.png")

    comparison: list[Image.Image] = []
    comparison_labels: list[str] = []
    for version in ("v1", "v2", "v3", "v4"):
        states = actual_380 if version == "v4" else {
            state: rgba(PUBLIC / f"{state}-{version}.webp").resize((380, 380), Image.Resampling.LANCZOS)
            for state in STATES
        }
        for weight in (0.10, 0.25, 0.50, 0.75):
            comparison.append(on_background(copy_lighter_mix(states, 0.0, weight), "#233048"))
            comparison_labels.append(f"{version} / roar {int(weight * 100)}%")
    labeled_sheet(comparison, comparison_labels, 4, 380).save(AUDIT / "v1-v2-v3-v4-roar-compare-380.png")

    topology_pass = True
    gap_pass = True
    for weight in (0.10, 0.25, 0.50, 0.75):
        metrics = weight_metrics[f"{weight:.2f}"]
        for result in metrics["delta_e76"].values():
            if int(result["joined_significant_component_count"]) != 1:
                topology_pass = False
        if int(metrics["cream_gap"]["cream_rows_between_nose_and_mouth"] or 0) < 5:
            gap_pass = False

    hard = np.asarray(hard_cavity) > 250
    target_array = np.asarray(roar_target_rgb)
    cavity_rgb = target_array[hard]
    alpha_hashes = {
        state: hashlib.sha256(masters[state].getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }
    neutral_array = np.asarray(neutral, dtype=np.int16)
    outside = np.asarray(edit_mask) == 0
    manifest: dict[str, object] = {
        "animal": "sloth",
        "name": "Sleepy Sloth",
        "version": VERSION,
        "repair_scope": "new deterministic mouth from accepted v1 neutral; v1-v3 preserved",
        "generation_route": "v1 neutral RGB only; sampled muzzle erase plus one uniform cocoa cavity; no ImageGen",
        "cavity_geometry_native": {"ellipse_xyxy": [574, 858, 680, 958], "cream_strip_preserved_through_y": 857},
        "cavity_tonal_family": {
            "mean_rgb": [round(float(value), 4) for value in cavity_rgb.mean(axis=0)],
            "stddev_rgb": [round(float(value), 4) for value in cavity_rgb.std(axis=0)],
            "min_rgb": [int(value) for value in cavity_rgb.min(axis=0)],
            "max_rgb": [int(value) for value in cavity_rgb.max(axis=0)],
        },
        "runtime_export": {"side_px": chosen_side, "quality": chosen_quality, "alpha_quality": 100, "method": 6},
        "candidate_sizes_bytes": {f"{side}-q{quality}": values for (side, quality), values in candidates.items()},
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "neutral_v1_v4_file_sha256_equal": sha256(ALPHA / "neutral-v1.png") == sha256(ALPHA / "neutral-v4.png"),
        "blink_v1_v4_file_sha256_equal": sha256(ALPHA / "blink-v1.png") == sha256(ALPHA / "blink-v4.png"),
        "roar_outside_localization_max_channel_delta": int(
            np.abs(np.asarray(roar, dtype=np.int16) - neutral_array)[outside].max()
        ),
        "topology": {
            "all_requested_weights_connected_at_all_delta_e_thresholds": topology_pass,
            "all_requested_weights_have_at_least_5px_cream_gap": gap_pass,
            "delta_e_thresholds": list(DELTA_E_THRESHOLDS),
            "luminance_thresholds": list(LUMINANCE_THRESHOLDS),
            "weights": weight_metrics,
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
    manifest["deterministic_target"] = {"path": str(roar_target_path.relative_to(ROOT)), "sha256": sha256(roar_target_path)}
    (AUDIT / "manifest-v4.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
