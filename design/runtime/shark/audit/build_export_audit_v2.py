#!/usr/bin/env python3
"""Repair Silly Shark's roar transition topology non-destructively as v2."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from build_export_audit import (
    ALPHA,
    AUDIT,
    CHROMA,
    PAGES,
    PUBLIC,
    ROOT,
    STATES,
    alpha_metrics,
    checker,
    composite_over,
    copy_lighter_mix,
    labeled_sheet,
    sha256,
)


VERSION = "v2"
CANVAS = (1254, 1254)
PROOF_WEIGHTS = (0.0, 0.10, 0.25, 0.50, 0.75, 1.0)
PERCEPTUAL_THRESHOLDS = (105, 115, 125, 135, 145, 155, 165, 175, 185)
PROBE_ROI = (142, 270, 238, 328)
NATIVE_REPAIR_ROI = (468, 892, 786, 1114)


def components(binary: np.ndarray) -> list[dict[str, object]]:
    height, width = binary.shape
    seen = np.zeros_like(binary, dtype=bool)
    found: list[dict[str, object]] = []
    for start_y, start_x in zip(*np.where(binary & ~seen)):
        if seen[start_y, start_x]:
            continue
        queue: deque[tuple[int, int]] = deque([(int(start_y), int(start_x))])
        seen[start_y, start_x] = True
        points: list[tuple[int, int]] = []
        while queue:
            y, x = queue.popleft()
            points.append((y, x))
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if (
                    0 <= ny < height
                    and 0 <= nx < width
                    and binary[ny, nx]
                    and not seen[ny, nx]
                ):
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        ys = np.array([point[0] for point in points])
        xs = np.array([point[1] for point in points])
        found.append(
            {
                "area": len(points),
                "bbox_xyxy": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                "centroid_xy": [round(float(xs.mean()), 3), round(float(ys.mean()), 3)],
            }
        )
    return sorted(found, key=lambda item: int(item["area"]), reverse=True)


def connected_component(candidate: np.ndarray, seed: tuple[int, int]) -> np.ndarray:
    if not candidate[seed]:
        raise RuntimeError(f"Seed {seed} is outside its intended component")
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
    return connected


def luminance(rgb: np.ndarray) -> np.ndarray:
    return (
        rgb[..., 0].astype(np.float32) * 0.2126
        + rgb[..., 1].astype(np.float32) * 0.7152
        + rgb[..., 2].astype(np.float32) * 0.0722
    )


def smoothstep(value: np.ndarray) -> np.ndarray:
    safe = np.clip(value, 0.0, 1.0)
    return safe * safe * (3.0 - 2.0 * safe)


def build_roar_v2(neutral: Image.Image, roar_v1: Image.Image) -> tuple[Image.Image, dict[str, int]]:
    neutral_rgb = np.asarray(neutral.convert("RGB"), dtype=np.uint8)
    roar_rgb = np.asarray(roar_v1.convert("RGB"), dtype=np.uint8)
    output = roar_rgb.copy()
    yy, xx = np.mgrid[0 : CANVAS[1], 0 : CANVAS[0]]

    # Select only the neutral smile's connected dark component. This is the
    # exact 257px span the critic identified, with no nose or cheek pixels.
    neutral_luma = luminance(neutral_rgb)
    smile_candidate = (
        (xx >= 480)
        & (xx < 770)
        & (yy >= 910)
        & (yy < 1000)
        & (neutral_luma < 170)
    )
    smile_component = connected_component(smile_candidate, (978, 625))

    # Hard-limit every modified pixel to the declared repair ROI so outside-ROI
    # equality is exact even after mask feathering.
    x0, y0, x1, y1 = NATIVE_REPAIR_ROI
    roi = ((xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)).astype(np.float32)

    # First restore exact neutral muzzle texture throughout the old mouth area.
    # This removes v1's compact cavity, teeth, and discrete tongue before the
    # replacement is drawn; roar brows and every pixel outside the ROI survive.
    cleanup = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(cleanup).rounded_rectangle((472, 896, 782, 1110), radius=84, fill=255)
    cleanup = cleanup.filter(ImageFilter.GaussianBlur(12.0))
    cleanup_mix = (np.asarray(cleanup, dtype=np.float32) / 255.0 * roi)[..., None]
    output = np.clip(
        output.astype(np.float32) * (1.0 - cleanup_mix)
        + neutral_rgb.astype(np.float32) * cleanup_mix,
        0,
        255,
    ).astype(np.uint8)

    # Draw one smooth mouth whose upper edge follows the accepted neutral smile
    # from x=492 to x=758. The old smile therefore becomes the cavity boundary,
    # not a bar crossing a smaller O. Curved sides taper to the lower center, so
    # no side hook can exist independently at any blend weight.
    supersample = 4

    def quadratic(
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        count: int,
    ) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for index in range(count):
            t = index / (count - 1)
            one = 1.0 - t
            points.append(
                (
                    one * one * p0[0] + 2.0 * one * t * p1[0] + t * t * p2[0],
                    one * one * p0[1] + 2.0 * one * t * p1[1] + t * t * p2[1],
                )
            )
        return points

    def cubic(
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
        count: int,
    ) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for index in range(count):
            t = index / (count - 1)
            one = 1.0 - t
            points.append(
                (
                    one**3 * p0[0]
                    + 3.0 * one * one * t * p1[0]
                    + 3.0 * one * t * t * p2[0]
                    + t**3 * p3[0],
                    one**3 * p0[1]
                    + 3.0 * one * one * t * p1[1]
                    + 3.0 * one * t * t * p2[1]
                    + t**3 * p3[1],
                )
            )
        return points

    mouth_points = (
        quadratic((492, 924), (548, 974), (625, 982), 48)
        + quadratic((625, 982), (702, 974), (758, 924), 48)[1:]
        + cubic((758, 924), (752, 1006), (704, 1086), (625, 1098), 64)[1:]
        + cubic((625, 1098), (546, 1086), (498, 1006), (492, 924), 64)[1:]
    )
    cavity_high = Image.new("L", (CANVAS[0] * supersample, CANVAS[1] * supersample), 0)
    ImageDraw.Draw(cavity_high).polygon(
        [(round(x * supersample), round(y * supersample)) for x, y in mouth_points],
        fill=255,
    )
    cavity_image = cavity_high.resize(CANVAS, Image.Resampling.LANCZOS)
    cavity_mask = np.asarray(cavity_image, dtype=np.float32) / 255.0 * roi

    # A narrow 2.5D cocoa rim grounds the opening against the cream muzzle.
    dilated = cavity_image.filter(ImageFilter.MaxFilter(19)).filter(ImageFilter.GaussianBlur(1.5))
    rim_mask = np.clip(
        np.asarray(dilated, dtype=np.float32) / 255.0 - cavity_mask,
        0.0,
        1.0,
    ) * roi
    rim_t = smoothstep((yy.astype(np.float32) - 930.0) / 168.0)
    rim_top = np.array([85.0, 42.0, 30.0], dtype=np.float32)
    rim_bottom = np.array([190.0, 120.0, 90.0], dtype=np.float32)
    rim_target = (
        rim_top[None, None, :] * (1.0 - rim_t[..., None])
        + rim_bottom[None, None, :] * rim_t[..., None]
    )
    rim_mix = rim_mask[..., None]
    output = np.clip(
        output.astype(np.float32) * (1.0 - rim_mix) + rim_target * rim_mix,
        0,
        255,
    ).astype(np.uint8)

    # One continuous dark-to-warm interior provides tongue warmth without a
    # discrete oval island. The darkest pixels sit directly beneath the neutral
    # smile boundary, so every perceptual threshold grows downward from it.
    texture = (
        np.sin(xx.astype(np.float32) * 0.171)
        + np.sin(yy.astype(np.float32) * 0.137)
    ) * 1.8
    cavity_t = smoothstep((yy.astype(np.float32) - 975.0) / 123.0)
    cavity_top = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    cavity_bottom = np.array([225.0, 145.0, 112.0], dtype=np.float32)
    cavity_target = (
        cavity_top[None, None, :] * (1.0 - cavity_t[..., None])
        + cavity_bottom[None, None, :] * cavity_t[..., None]
        + texture[..., None]
    )
    cavity_mix = cavity_mask[..., None]
    output = np.clip(
        output.astype(np.float32) * (1.0 - cavity_mix) + cavity_target * cavity_mix,
        0,
        255,
    ).astype(np.uint8)

    # Exactly two small rounded tooth caps attach to the upper boundary. They
    # are newly deterministic, softly shaded, and never pointed.
    teeth_high = Image.new("L", (CANVAS[0] * supersample, CANVAS[1] * supersample), 0)
    teeth_draw = ImageDraw.Draw(teeth_high)
    for box in ((557, 948, 597, 994), (657, 948, 697, 994)):
        scaled_box = tuple(round(value * supersample) for value in box)
        teeth_draw.rounded_rectangle(scaled_box, radius=14 * supersample, fill=255)
    teeth_image = teeth_high.resize(CANVAS, Image.Resampling.LANCZOS)
    teeth_mask = (
        np.asarray(teeth_image, dtype=np.float32) / 255.0 * cavity_mask * roi
    )
    tooth_t = smoothstep((yy.astype(np.float32) - 950.0) / 48.0)
    tooth_top = np.array([255.0, 250.0, 229.0], dtype=np.float32)
    tooth_bottom = np.array([231.0, 198.0, 164.0], dtype=np.float32)
    tooth_target = (
        tooth_top[None, None, :] * (1.0 - tooth_t[..., None])
        + tooth_bottom[None, None, :] * tooth_t[..., None]
        + texture[..., None] * 0.25
    )
    tooth_mix = teeth_mask[..., None]
    output = np.clip(
        output.astype(np.float32) * (1.0 - tooth_mix) + tooth_target * tooth_mix,
        0,
        255,
    ).astype(np.uint8)

    alpha = neutral.getchannel("A")
    repaired = Image.fromarray(output).convert("RGBA")
    repaired.putalpha(alpha)
    return repaired, {
        "neutral_smile_component_pixels": int(smile_component.sum()),
        "cleanup_nonzero_pixels": int((cleanup_mix[..., 0] > 0).sum()),
        "rim_nonzero_pixels": int((rim_mask > 0).sum()),
        "cavity_nonzero_pixels": int((cavity_mask > 0).sum()),
        "tooth_nonzero_pixels": int((teeth_mask > 0).sum()),
    }


def component_profile(image: Image.Image) -> dict[str, object]:
    x0, y0, x1, y1 = PROBE_ROI
    rgb = np.asarray(image.convert("RGB"))[y0:y1, x0:x1]
    luma = luminance(rgb)
    profiles: dict[str, object] = {}
    for threshold in PERCEPTUAL_THRESHOLDS:
        binary = luma < threshold
        # The two intentional bright tooth caps are holes inside one cavity,
        # not separate mouth components. Fill only their known local boxes for
        # topology connectivity; detached lower forms remain untouched.
        topology_binary = binary.copy()
        topology_binary[17:32, 27:40] = True
        topology_binary[17:32, 57:70] = True
        significant = [
            component for component in components(topology_binary) if int(component["area"]) >= 64
        ]
        largest = significant[0] if significant else None
        profiles[str(threshold)] = {
            "significant_component_count": len(significant),
            "components": significant[:6],
            "visible_pixels": int(binary.sum()),
            "single_connected_mouth": bool(
                len(significant) == 1
                and int(significant[0]["bbox_xyxy"][0]) <= 11
                and int(significant[0]["bbox_xyxy"][2]) >= 84
            )
            if largest
            else False,
        }
    return {"roi_xyxy": list(PROBE_ROI), "thresholds": profiles}


def gallery_roar_weight(progress: float) -> float:
    safe = min(1.0, max(0.0, progress))
    eased = safe * safe * (3.0 - 2.0 * safe)
    mouth = 0.08 + 0.92 * eased
    return min(1.0, max(0.0, (mouth - 0.08) * 1.22))


def save_ramp(states: dict[str, Image.Image], side: int, path: Path) -> list[dict[str, object]]:
    frames: list[Image.Image] = []
    metrics: list[dict[str, object]] = []
    count = 24
    for index in range(count):
        progress = index / (count - 1)
        weight = gallery_roar_weight(progress)
        mixed = copy_lighter_mix(states, 0.0, weight)
        proof = composite_over(mixed, (35, 48, 72), side)
        frames.append(proof)
        metrics.append(
            {
                "frame": index,
                "time_ms": round(index * (936 / (count - 1)), 3),
                "production_roar_weight": round(weight, 6),
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


def webp_bytes(image: Image.Image, quality: int) -> bytes:
    stream = io.BytesIO()
    image.save(stream, "WEBP", quality=quality, alpha_quality=100, method=6, exact=True)
    return stream.getvalue()


def main() -> None:
    neutral_v1 = Image.open(ALPHA / "neutral-v1.png").convert("RGBA")
    blink_v1 = Image.open(ALPHA / "blink-v1.png").convert("RGBA")
    roar_v1 = Image.open(ALPHA / "roar-v1.png").convert("RGBA")
    roar_v2, geometry_metrics = build_roar_v2(neutral_v1, roar_v1)

    # Neutral runtime is byte-identical, so the measured canonical coverage
    # proof is also byte-identical and receives a v2 audit filename.
    shutil.copy2(
        AUDIT / "canonical-forehead-geometry-v1.png",
        AUDIT / "canonical-forehead-geometry-v2.png",
    )

    # Preserve accepted neutral/blink source files exactly. v2 roar alone is new.
    shutil.copy2(ALPHA / "neutral-v1.png", ALPHA / "neutral-v2.png")
    shutil.copy2(ALPHA / "blink-v1.png", ALPHA / "blink-v2.png")
    roar_v2.save(ALPHA / "roar-v2.png", optimize=True)
    shutil.copy2(CHROMA / "neutral-v1.png", CHROMA / "neutral-v2.png")
    shutil.copy2(CHROMA / "blink-v1.png", CHROMA / "blink-v2.png")
    chroma = Image.new("RGBA", CANVAS, "#00ff00")
    chroma.alpha_composite(roar_v2)
    chroma.convert("RGB").save(CHROMA / "roar-v2.png", optimize=True)

    shutil.copy2(PUBLIC / "neutral-v1.webp", PUBLIC / "neutral-v2.webp")
    shutil.copy2(PUBLIC / "blink-v1.webp", PUBLIC / "blink-v2.webp")
    shutil.copy2(PUBLIC / "neutral-v2.webp", PAGES / "neutral-v2.webp")
    shutil.copy2(PUBLIC / "blink-v2.webp", PAGES / "blink-v2.webp")
    roar_candidates = {quality: webp_bytes(roar_v2, quality) for quality in (95, 94)}
    roar_quality = next(
        (quality for quality in (95, 94) if 200_000 <= len(roar_candidates[quality]) <= 350_000),
        None,
    )
    if roar_quality is None:
        raise RuntimeError(
            f"No 1254px q94-95 roar export met 200-350KB: "
            f"{ {quality: len(blob) for quality, blob in roar_candidates.items()} }"
        )
    (PUBLIC / "roar-v2.webp").write_bytes(roar_candidates[roar_quality])
    shutil.copy2(PUBLIC / "roar-v2.webp", PAGES / "roar-v2.webp")

    runtime = {
        state: Image.open(PUBLIC / f"{state}-v2.webp").convert("RGBA") for state in STATES
    }
    actual_380 = {
        state: image.resize((380, 380), Image.Resampling.LANCZOS) for state, image in runtime.items()
    }
    actual_96 = {
        state: image.resize((96, 96), Image.Resampling.LANCZOS) for state, image in runtime.items()
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
        stills_380.append(composite_over(mixed_380, (35, 48, 72), 380))
        stills_96.append(
            composite_over(mixed_96, (35, 48, 72), 96).resize(
                (380, 380), Image.Resampling.NEAREST
            )
        )
        weight_profiles[f"{weight:.2f}"] = component_profile(mixed_380)
    labeled_sheet(stills_380, labels, 3, 380).save(AUDIT / "production-roar-weights-380-v2.png")
    labeled_sheet(stills_96, [f"{label} / 96px 4x" for label in labels], 3, 380).save(
        AUDIT / "production-roar-weights-96-v2.png"
    )

    threshold_images: list[Image.Image] = []
    threshold_labels: list[str] = []
    probe_x0, probe_y0, probe_x1, probe_y1 = PROBE_ROI
    for weight in (0.10, 0.25, 0.50, 0.75):
        mixed = copy_lighter_mix(actual_380, 0.0, weight)
        crop = np.asarray(mixed.convert("RGB"))[probe_y0:probe_y1, probe_x0:probe_x1]
        probe_luma = luminance(crop)
        for threshold in (125, 145, 165, 185):
            binary = (probe_luma < threshold).astype(np.uint8) * 255
            threshold_images.append(
                Image.fromarray(binary).convert("RGB").resize((380, 380), Image.Resampling.NEAREST)
            )
            threshold_labels.append(f"roar {int(weight * 100)}% / L*<{threshold}")
    labeled_sheet(threshold_images, threshold_labels, 4, 380).save(
        AUDIT / "perceptual-component-thresholds-v2.png"
    )

    ramp_metrics_380 = save_ramp(actual_380, 380, AUDIT / "production-roar-ramp-936ms-380-v2.gif")
    ramp_metrics_96 = save_ramp(actual_380, 96, AUDIT / "production-roar-ramp-936ms-96-v2.gif")

    native = [composite_over(Image.open(ALPHA / f"{state}-v2.png"), (237, 240, 245), 380) for state in STATES]
    labeled_sheet(native, [f"{state} / v2" for state in STATES], 3, 380).save(
        AUDIT / "states-380-v2.png"
    )
    hostile: list[Image.Image] = []
    hostile_labels: list[str] = []
    for background_name, background in (
        ("white", (255, 255, 255)),
        ("black", (0, 0, 0)),
        ("cyan", (0, 220, 255)),
        ("magenta", (255, 0, 220)),
    ):
        for state in STATES:
            hostile.append(composite_over(actual_380[state], background, 380))
            hostile_labels.append(f"{state} / {background_name}")
    labeled_sheet(hostile, hostile_labels, 3, 380).save(AUDIT / "hostile-380-states-v2.png")

    comparison: list[Image.Image] = []
    comparison_labels: list[str] = []
    v1_runtime = {
        state: Image.open(PUBLIC / f"{state}-v1.webp").convert("RGBA").resize(
            (380, 380), Image.Resampling.LANCZOS
        )
        for state in STATES
    }
    for version, states in (("v1", v1_runtime), ("v2", actual_380)):
        for weight in (0.10, 0.25, 0.50, 0.75, 1.0):
            comparison.append(composite_over(copy_lighter_mix(states, 0.0, weight), (35, 48, 72), 380))
            comparison_labels.append(f"{version} / roar {int(weight * 100)}%")
    labeled_sheet(comparison, comparison_labels, 5, 380).save(
        AUDIT / "v1-v2-roar-compare-380.png"
    )

    requested_weights = (0.10, 0.25, 0.50, 0.75)
    single_component_all = True
    for weight in requested_weights:
        thresholds = weight_profiles[f"{weight:.2f}"]["thresholds"]
        for threshold in PERCEPTUAL_THRESHOLDS:
            if int(thresholds[str(threshold)]["significant_component_count"]) != 1:
                single_component_all = False

    master_alpha_hashes = {
        state: hashlib.sha256(
            Image.open(ALPHA / f"{state}-v2.png").convert("RGBA").getchannel("A").tobytes()
        ).hexdigest()
        for state in STATES
    }
    runtime_alpha_hashes = {
        state: hashlib.sha256(runtime[state].getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }
    v1_array = np.asarray(roar_v1, dtype=np.int16)
    v2_array = np.asarray(roar_v2, dtype=np.int16)
    x0, y0, x1, y1 = NATIVE_REPAIR_ROI
    outside = np.ones((CANVAS[1], CANVAS[0]), dtype=bool)
    outside[y0:y1, x0:x1] = False

    manifest: dict[str, object] = {
        "animal": "shark",
        "name": "Silly Shark",
        "version": VERSION,
        "repair_scope": "roar mouth target geometry only; v1 retained; neutral, blink, shared alpha, identity, gills, skin, silhouette, padding, and matte preserved",
        "generation_route": "deterministic v2 from v1 alpha masters; no new ImageGen call",
        "provenance": "design/runtime/shark/audit/provenance-v2.md",
        "geometry_repair": {
            **geometry_metrics,
            "native_repair_roi_xyxy": list(NATIVE_REPAIR_ROI),
            "neutral_smile_critic_span_x": [496, 753],
            "v1_roar_cavity_critic_span_x": [545, 708],
            "final_tooth_count": 2,
            "final_tooth_shape": "small rounded-rectangle caps clipped to the continuous cavity",
            "strategy": "rebuild one smooth supersampled cavity whose upper Bezier edge follows and absorbs the exact connected neutral smile; use a continuous dark-to-warm interior; add exactly two rounded deterministic tooth caps",
        },
        "preservation": {
            "neutral_v1_v2_alpha_file_sha256_equal": sha256(ALPHA / "neutral-v1.png") == sha256(ALPHA / "neutral-v2.png"),
            "blink_v1_v2_alpha_file_sha256_equal": sha256(ALPHA / "blink-v1.png") == sha256(ALPHA / "blink-v2.png"),
            "neutral_v1_v2_chroma_file_sha256_equal": sha256(CHROMA / "neutral-v1.png") == sha256(CHROMA / "neutral-v2.png"),
            "blink_v1_v2_chroma_file_sha256_equal": sha256(CHROMA / "blink-v1.png") == sha256(CHROMA / "blink-v2.png"),
            "neutral_v1_v2_runtime_file_sha256_equal": sha256(PUBLIC / "neutral-v1.webp") == sha256(PUBLIC / "neutral-v2.webp"),
            "blink_v1_v2_runtime_file_sha256_equal": sha256(PUBLIC / "blink-v1.webp") == sha256(PUBLIC / "blink-v2.webp"),
            "roar_v1_v2_outside_roi_max_channel_delta": int(
                np.abs(v2_array - v1_array)[outside].max()
            ),
        },
        "runtime_export": {
            "side_px": 1254,
            "neutral_quality": 95,
            "blink_quality": 95,
            "roar_quality": roar_quality,
            "alpha_quality": 100,
            "method": 6,
            "roar_candidate_sizes_bytes": {
                str(quality): len(blob) for quality, blob in roar_candidates.items()
            },
        },
        "alpha_pixel_hashes": master_alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(master_alpha_hashes.values())) == 1,
        "runtime_decoded_alpha_pixel_hashes": runtime_alpha_hashes,
        "runtime_decoded_alpha_pixel_hashes_identical": len(set(runtime_alpha_hashes.values())) == 1,
        "canonical_geometry_preserved_by_byte_identical_neutral_runtime": sha256(PUBLIC / "neutral-v1.webp") == sha256(PUBLIC / "neutral-v2.webp"),
        "canonical_geometry": json.loads((AUDIT / "manifest-v1.json").read_text())["canonical_geometry"],
        "perceptual_component_probe": {
            "thresholds": list(PERCEPTUAL_THRESHOLDS),
            "minimum_significant_component_area_px": 64,
            "tooth_aware_connectivity": "the two known intentional bright tooth boxes are filled before connected-component counting; all other pixels use raw luminance",
            "all_requested_weights_single_component_at_all_thresholds": single_component_all,
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
    masters = {
        state: Image.open(ALPHA / f"{state}-v2.png").convert("RGBA") for state in STATES
    }
    for state, image in masters.items():
        alpha_path = ALPHA / f"{state}-v2.png"
        chroma_path = CHROMA / f"{state}-v2.png"
        public_path = PUBLIC / f"{state}-v2.webp"
        pages_path = PAGES / f"{state}-v2.webp"
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
            "has_alph_chunk": b"ALPH" in public_path.read_bytes(),
            "metrics": alpha_metrics(image),
        }
    (AUDIT / "manifest-v2.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
