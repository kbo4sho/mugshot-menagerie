#!/usr/bin/env python3
"""Build and audit the four-state Sloth v5 bridge from accepted v1 assets."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from build_export_audit import (
    CANVAS,
    ROOT,
    alpha_metrics,
    checker,
    labeled_sheet,
    on_background,
    rgba,
    sha256,
)
from build_export_audit_v2 import components, gallery_roar_weight


ANIMAL = ROOT / "design/runtime/sloth"
AUDIT = ANIMAL / "audit"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
PUBLIC = ROOT / "public/masks/sloth"
PAGES = ROOT / "github-pages/public/masks/sloth"
HELPER = ROOT / "app/rendered-mask-blend.mjs"
VERSION = "v5"
STATES = ("neutral", "blink", "roar-mid", "roar")
JAW_WEIGHTS = (0.0, 0.10, 0.25, 0.50, 0.75, 1.0)
LUMINANCE_THRESHOLDS = (75, 90, 105, 120, 135, 150, 165)
MOUTH_ROI = (170, 255, 210, 293)
LOCALIZATION_ROI = (515, 815, 725, 970)


def luminance(rgb: np.ndarray) -> np.ndarray:
    return (
        rgb[..., 0].astype(np.float32) * 0.2126
        + rgb[..., 1].astype(np.float32) * 0.7152
        + rgb[..., 2].astype(np.float32) * 0.0722
    )


def significant(binary: np.ndarray, minimum: int = 7) -> list[dict[str, object]]:
    return [entry for entry in components(binary) if int(entry["area"]) >= minimum]


def connected_from_seed(binary: np.ndarray, seed: tuple[int, int]) -> np.ndarray:
    if not binary[seed]:
        raise RuntimeError(f"Seed {seed} is not inside the candidate mask")
    connected = np.zeros_like(binary, dtype=bool)
    queue: deque[tuple[int, int]] = deque([seed])
    connected[seed] = True
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if (
                0 <= ny < binary.shape[0]
                and 0 <= nx < binary.shape[1]
                and binary[ny, nx]
                and not connected[ny, nx]
            ):
                connected[ny, nx] = True
                queue.append((ny, nx))
    return connected


def smile_component(neutral_rgb: Image.Image) -> np.ndarray:
    array = np.asarray(neutral_rgb)
    lum = luminance(array)
    candidate = np.zeros((CANVAS[1], CANVAS[0]), dtype=bool)
    candidate[825:880, 515:725] = lum[825:880, 515:725] < 155
    # The center-bottom pixel is on the accepted neutral smile, below the nose.
    return connected_from_seed(candidate, (866, 627))


def smooth_curve(values: np.ndarray, radius: int = 5) -> np.ndarray:
    padded = np.pad(values, (radius, radius), mode="edge")
    kernel = np.ones(radius * 2 + 1, dtype=np.float64) / (radius * 2 + 1)
    return np.convolve(padded, kernel, mode="valid")


def cavity_mask_from_smile(
    smile: np.ndarray,
    x_left: int,
    x_right: int,
    center_depth: float,
    edge_depth: float,
) -> tuple[Image.Image, list[float], list[float]]:
    xs = np.arange(x_left, x_right + 1)
    upper: list[float] = []
    for x in xs:
        ys = np.where(smile[:, x])[0]
        if len(ys) == 0:
            raise RuntimeError(f"Accepted smile has no dark pixels at x={x}")
        upper.append(float(ys.min()))
    upper_array = smooth_curve(np.asarray(upper), 4)
    t = np.abs((xs.astype(np.float64) - xs.mean()) / ((x_right - x_left) / 2.0))
    depth = edge_depth + (center_depth - edge_depth) * np.power(np.clip(1.0 - t * t, 0, 1), 0.72)
    lower_array = upper_array + depth

    polygon: list[tuple[float, float]] = [
        (float(x), float(y - 1.5)) for x, y in zip(xs, upper_array)
    ]
    polygon.extend(
        (float(x), float(y)) for x, y in zip(xs[::-1], lower_array[::-1])
    )
    hard = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(hard).polygon(polygon, fill=255)
    return hard.filter(ImageFilter.GaussianBlur(1.35)), upper_array.tolist(), lower_array.tolist()


def build_targets(
    neutral: Image.Image,
) -> tuple[Image.Image, Image.Image, dict[str, Image.Image], dict[str, object]]:
    neutral_rgb = neutral.convert("RGB")
    array = np.asarray(neutral_rgb, dtype=np.uint8)
    smile = smile_component(neutral_rgb)
    smile_image = Image.fromarray(smile.astype(np.uint8) * 255)

    # Remove the accepted smile only outside the shared authored upper rim. The
    # center is repainted by both cavity masks, while side segments receive real
    # cream muzzle texture sampled from the same face directly below them.
    side_selector = np.ones((CANVAS[1], CANVAS[0]), dtype=np.uint8) * 255
    side_selector[:, 574:681] = 0
    side_mask = ImageChops.multiply(
        smile_image.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(1.5)),
        Image.fromarray(side_selector),
    )
    sampled = array.copy()
    sampled[:-34] = array[34:]
    sampled_image = Image.fromarray(sampled)
    base = Image.composite(sampled_image, neutral_rgb, side_mask)

    mid_mask, upper_mid, lower_mid = cavity_mask_from_smile(smile, 574, 680, 43, 10)
    roar_mask, upper_roar, lower_roar = cavity_mask_from_smile(smile, 574, 680, 112, 13)
    if max(abs(a - b) for a, b in zip(upper_mid, upper_roar)) > 1e-8:
        raise RuntimeError("Mid and roar upper rims diverged")

    yy, xx = np.mgrid[0 : CANVAS[1], 0 : CANVAS[0]]
    micro = (np.sin(xx * 0.151) + np.sin(yy * 0.137)) * 0.75
    cocoa = np.empty((CANVAS[1], CANVAS[0], 3), dtype=np.float32)
    cocoa[..., 0] = 55.0 + micro
    cocoa[..., 1] = 25.0 + micro * 0.35
    cocoa[..., 2] = 16.0 + micro * 0.25
    cocoa_image = Image.fromarray(np.clip(np.rint(cocoa), 0, 255).astype(np.uint8))
    mid = Image.composite(cocoa_image, base, mid_mask)
    roar = Image.composite(cocoa_image, base, roar_mask)

    masks = {
        "accepted-smile": smile_image,
        "smile-side-erase": side_mask,
        "mid-cavity": mid_mask,
        "roar-cavity": roar_mask,
        "mid-edit": ImageChops.lighter(side_mask, mid_mask),
        "roar-edit": ImageChops.lighter(side_mask, roar_mask),
    }
    geometry = {
        "x_span_native_inclusive": [574, 680],
        "upper_rim_native_y_min_max": [round(min(upper_mid), 3), round(max(upper_mid), 3)],
        "mid_lower_native_y_min_max": [round(min(lower_mid), 3), round(max(lower_mid), 3)],
        "roar_lower_native_y_min_max": [round(min(lower_roar), 3), round(max(lower_roar), 3)],
        "mid_center_depth_native": 43,
        "roar_center_depth_native": 112,
        "shared_upper_rim_exact": True,
    }
    return mid, roar, masks, geometry


def helper_weights(jaw_values: list[float]) -> list[dict[str, float]]:
    script = (
        "import {getRenderedMaskBlendWeights as g} from "
        + json.dumps(HELPER.as_uri())
        + "; const values="
        + json.dumps(jaw_values)
        + "; console.log(JSON.stringify(values.map(v=>({jaw:v,...g(0,v,true)}))));"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def mix(states: dict[str, Image.Image], weights: dict[str, float]) -> Image.Image:
    mapping = {
        "neutral": float(weights["neutral"]),
        "blink": float(weights["blink"]),
        "roar-mid": float(weights["roarMid"]),
        "roar": float(weights["roar"]),
    }
    arrays = {
        state: np.asarray(states[state], dtype=np.float32) / 255.0 for state in STATES
    }
    alpha = sum(mapping[state] * arrays[state][..., 3:4] for state in STATES)
    rgbp = sum(
        mapping[state] * arrays[state][..., :3] * arrays[state][..., 3:4]
        for state in STATES
    )
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    return Image.fromarray(
        np.clip(np.rint(np.concatenate((rgb, alpha), axis=2) * 255), 0, 255).astype(np.uint8)
    )


def cream_gap_metrics(image: Image.Image) -> dict[str, object]:
    rgb = np.asarray(image.convert("RGB"))
    lum = luminance(rgb)
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
    strip = rgb[251:257, 184:197]
    return {
        "center_dark_row_groups": [[group[0], group[-1]] for group in meaningful],
        "cream_rows_between_nose_and_mouth": gap,
        "fixed_strip_roi_xyxy": [184, 251, 197, 257],
        "fixed_strip_min_luminance": round(float(luminance(strip).min()), 4),
        "fixed_strip_mean_luminance": round(float(luminance(strip).mean()), 4),
    }


def mouth_metrics(image: Image.Image) -> dict[str, object]:
    rgb = np.asarray(image.convert("RGB"))
    x0, y0, x1, y1 = MOUTH_ROI
    roi_lum = luminance(rgb[y0:y1, x0:x1])
    threshold_profiles: dict[str, object] = {}
    for threshold in LUMINANCE_THRESHOLDS:
        found = significant(roi_lum < threshold, 7)
        threshold_profiles[str(threshold)] = {
            "significant_component_count": len(found),
            "components": found[:3],
        }
    return {
        "roi_xyxy": list(MOUTH_ROI),
        "perceptual_luminance": threshold_profiles,
        "cream_gap": cream_gap_metrics(image),
    }


def save_ramp(
    states: dict[str, Image.Image], side: int, path: Path
) -> list[dict[str, object]]:
    frames: list[Image.Image] = []
    metrics: list[dict[str, object]] = []
    count = 24
    jaw_values = [gallery_roar_weight(index / (count - 1)) for index in range(count)]
    resolved = helper_weights(jaw_values)
    previous: Image.Image | None = None
    for index, (jaw, weights) in enumerate(zip(jaw_values, resolved)):
        mixed = mix(states, weights)
        proof = on_background(mixed, "#233048")
        if side == 96:
            proof = proof.resize((96, 96), Image.Resampling.LANCZOS)
        frames.append(proof)
        measured = mixed if side == 380 else mixed.resize((96, 96), Image.Resampling.LANCZOS)
        delta = 0.0
        if previous is not None:
            delta = float(
                np.abs(
                    np.asarray(measured.convert("RGB"), dtype=np.int16)
                    - np.asarray(previous.convert("RGB"), dtype=np.int16)
                ).mean()
            )
        previous = measured
        metrics.append(
            {
                "frame": index,
                "time_ms": round(index * (936 / (count - 1)), 3),
                "production_jaw_weight": round(jaw, 6),
                "helper_weights": {
                    key: round(float(weights[key]), 6)
                    for key in ("neutral", "blink", "roarMid", "roar")
                },
                "mean_abs_rgb_delta_from_previous_frame": round(delta, 6),
            }
        )
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=40,
        loop=0,
        optimize=False,
        disposal=2,
    )
    return metrics


def main() -> None:
    for directory in (AUDIT, CHROMA, ALPHA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    neutral = rgba(ALPHA / "neutral-v1.png")
    blink = rgba(ALPHA / "blink-v1.png")
    mid_rgb, roar_rgb, masks, cavity_geometry = build_targets(neutral)
    for name, mask in masks.items():
        mask.save(AUDIT / f"{name}-mask-v5.png", optimize=True)
    mid_rgb.save(AUDIT / "deterministic-roar-mid-target-v5.png", optimize=True)
    roar_rgb.save(AUDIT / "deterministic-roar-target-v5.png", optimize=True)

    accepted_alpha = neutral.getchannel("A")
    mid = mid_rgb.convert("RGBA")
    mid.putalpha(accepted_alpha)
    roar = roar_rgb.convert("RGBA")
    roar.putalpha(accepted_alpha)
    masters = {"neutral": neutral, "blink": blink, "roar-mid": mid, "roar": roar}
    for state, image in masters.items():
        image.putalpha(accepted_alpha)
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
                path = AUDIT / f"candidate-{state}-{side}-q{quality}-v5.webp"
                runtime.save(path, "WEBP", quality=quality, alpha_quality=100, method=6, exact=True)
                sizes.append(path.stat().st_size)
            candidates[(side, quality)] = sizes
            if min(sizes) >= 200_000 and max(sizes) <= 350_000:
                chosen_side, chosen_quality = side, quality
                break
        if chosen_side is not None:
            break
    if chosen_side is None or chosen_quality is None:
        raise RuntimeError(f"No q94-95 v5 export met the required weight range: {candidates}")

    runtime: dict[str, Image.Image] = {}
    for state, image in masters.items():
        encoded = image if chosen_side == 1254 else image.resize((chosen_side, chosen_side), Image.Resampling.LANCZOS)
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        encoded.save(public_path, "WEBP", quality=chosen_quality, alpha_quality=100, method=6, exact=True)
        shutil.copy2(public_path, PAGES / public_path.name)
        runtime[state] = rgba(public_path)

    actual_380 = {
        state: runtime[state].resize((380, 380), Image.Resampling.LANCZOS) for state in STATES
    }
    resolved_weights = helper_weights(list(JAW_WEIGHTS))
    stills_380: list[Image.Image] = []
    stills_96: list[Image.Image] = []
    mouth_zooms: list[Image.Image] = []
    labels: list[str] = []
    weight_metrics: dict[str, object] = {}
    for jaw, weights in zip(JAW_WEIGHTS, resolved_weights):
        mixed_380 = mix(actual_380, weights)
        # Production blends decoded sources at the 380 px offscreen surface;
        # the 96 px audit is that exact result downsampled, not a 96 px remix.
        mixed_96 = mixed_380.resize((96, 96), Image.Resampling.LANCZOS)
        label = (
            f"jaw {jaw:.2f} / N {weights['neutral']:.2f} "
            f"M {weights['roarMid']:.2f} R {weights['roar']:.2f}"
        )
        labels.append(label)
        stills_380.append(on_background(mixed_380, "#233048"))
        stills_96.append(
            on_background(mixed_96, "#233048").resize((380, 380), Image.Resampling.NEAREST)
        )
        x0, y0, x1, y1 = MOUTH_ROI
        crop = on_background(mixed_380, "#ede7dd").crop((x0, y0, x1, y1))
        mouth_zooms.append(crop.resize((352, 368), Image.Resampling.NEAREST))
        weight_metrics[f"{jaw:.2f}"] = {
            "helper_weights": {
                key: round(float(weights[key]), 6)
                for key in ("neutral", "blink", "roarMid", "roar")
            },
            "mouth": mouth_metrics(mixed_380),
        }
    labeled_sheet(stills_380, labels, 3, 380).save(
        AUDIT / "helper-driven-roar-weights-380-v5.png"
    )
    labeled_sheet(stills_96, [f"{label} / 96px 4x" for label in labels], 3, 380).save(
        AUDIT / "helper-driven-roar-weights-96-v5.png"
    )
    labeled_sheet(mouth_zooms, labels, 3, 352).save(
        AUDIT / "helper-driven-mouth-zooms-v5.png"
    )

    ramp_380 = save_ramp(actual_380, 380, AUDIT / "helper-driven-roar-ramp-936ms-380-v5.gif")
    ramp_96 = save_ramp(actual_380, 96, AUDIT / "helper-driven-roar-ramp-936ms-96-v5.gif")

    native = [on_background(masters[state], checker(CANVAS, 48)) for state in STATES]
    labeled_sheet(native, [f"{state} / native v5" for state in STATES], 4, CANVAS[0]).save(
        AUDIT / "native-states-v5.jpg", quality=90
    )
    endpoint_380 = [on_background(actual_380[state], "#edf0f5") for state in STATES]
    labeled_sheet(endpoint_380, [f"{state} / 380" for state in STATES], 4, 380).save(
        AUDIT / "states-380-v5.png"
    )
    hostile_images: list[Image.Image] = []
    hostile_labels: list[str] = []
    for background in ("#101318", "#fff3cc", "#c51f5d"):
        for state in STATES:
            hostile_images.append(on_background(actual_380[state], background))
            hostile_labels.append(f"{state} / {background}")
    labeled_sheet(hostile_images, hostile_labels, 4, 380).save(AUDIT / "hostile-380-states-v5.png")

    neutral_array = np.asarray(neutral, dtype=np.int16)
    outside = np.ones((CANVAS[1], CANVAS[0]), dtype=bool)
    x0, y0, x1, y1 = LOCALIZATION_ROI
    outside[y0:y1, x0:x1] = False
    outside_deltas = {}
    for state in ("roar-mid", "roar"):
        delta = np.abs(np.asarray(masters[state], dtype=np.int16)[..., :3] - neutral_array[..., :3])
        outside_deltas[state] = int(delta[outside].max())

    alpha_hashes = {
        state: hashlib.sha256(np.asarray(masters[state].getchannel("A")).tobytes()).hexdigest()
        for state in STATES
    }
    runtime_alpha_hashes = {
        state: hashlib.sha256(np.asarray(runtime[state].getchannel("A")).tobytes()).hexdigest()
        for state in STATES
    }
    chroma_corner_rgbs = {
        state: [
            list(rgba(CHROMA / f"{state}-{VERSION}.png").convert("RGB").getpixel(point))
            for point in ((0, 0), (CANVAS[0] - 1, 0), (0, CANVAS[1] - 1), (CANVAS[0] - 1, CANVAS[1] - 1))
        ]
        for state in STATES
    }
    public_hashes = {
        state: sha256(PUBLIC / f"{state}-{VERSION}.webp") for state in STATES
    }
    pages_hashes = {
        state: sha256(PAGES / f"{state}-{VERSION}.webp") for state in STATES
    }
    manifest = {
        "animal": "sloth",
        "name": "Sleepy Sloth",
        "version": VERSION,
        "architecture": "four-state roarMid bridge",
        "generation_route": "deterministic localized paint from accepted v1 neutral; no ImageGen",
        "review_status": "awaiting independent critic; not self-approved",
        "source_paths": {
            "neutral": str(ALPHA / "neutral-v1.png"),
            "blink": str(ALPHA / "blink-v1.png"),
            "blend_helper": str(HELPER),
        },
        "blend_helper_sha256": sha256(HELPER),
        "cavity_geometry": cavity_geometry,
        "localization_roi_native_xyxy": list(LOCALIZATION_ROI),
        "outside_localization_max_rgb_delta": outside_deltas,
        "neutral_v1_v5_file_sha256_equal": sha256(ALPHA / "neutral-v1.png")
        == sha256(ALPHA / "neutral-v5.png"),
        "blink_v1_v5_file_sha256_equal": sha256(ALPHA / "blink-v1.png")
        == sha256(ALPHA / "blink-v5.png"),
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "runtime_alpha_pixel_hashes": runtime_alpha_hashes,
        "runtime_alpha_pixel_hashes_identical": len(set(runtime_alpha_hashes.values())) == 1,
        "chroma_corner_rgbs": chroma_corner_rgbs,
        "chroma_corners_exact_00ff00": all(
            corner == [0, 255, 0]
            for corners in chroma_corner_rgbs.values()
            for corner in corners
        ),
        "native_alpha_metrics": {
            state: alpha_metrics(masters[state]) for state in STATES
        },
        "runtime_alpha_metrics": {
            state: alpha_metrics(runtime[state]) for state in STATES
        },
        "candidate_sizes_bytes": {
            f"{side}-q{quality}": sizes for (side, quality), sizes in candidates.items()
        },
        "runtime_export": {
            "side_px": chosen_side,
            "quality": chosen_quality,
            "alpha_quality": 100,
            "method": 6,
            "sizes_bytes": {
                state: (PUBLIC / f"{state}-{VERSION}.webp").stat().st_size for state in STATES
            },
            "public_sha256": public_hashes,
            "pages_sha256": pages_hashes,
            "public_pages_hashes_identical": public_hashes == pages_hashes,
        },
        "helper_driven_requested_weights": weight_metrics,
        "gallery_ramp": {
            "production_source_duration_ms": 936,
            "sampled_frames": 24,
            "encoded_gif_duration_ms": 960,
            "metrics_380": ramp_380,
            "metrics_96": ramp_96,
        },
        "evidence_paths": [
            str(AUDIT / "helper-driven-roar-weights-380-v5.png"),
            str(AUDIT / "helper-driven-roar-weights-96-v5.png"),
            str(AUDIT / "helper-driven-mouth-zooms-v5.png"),
            str(AUDIT / "helper-driven-roar-ramp-936ms-380-v5.gif"),
            str(AUDIT / "helper-driven-roar-ramp-936ms-96-v5.gif"),
            str(AUDIT / "native-states-v5.jpg"),
            str(AUDIT / "hostile-380-states-v5.png"),
        ],
    }
    (AUDIT / "manifest-v5.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
