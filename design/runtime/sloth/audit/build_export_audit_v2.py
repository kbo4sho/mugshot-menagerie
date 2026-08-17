#!/usr/bin/env python3
"""Repair the Sloth roar transition non-destructively as v2."""

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


ANIMAL = ROOT / "design/runtime/sloth"
AUDIT = ANIMAL / "audit"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
PUBLIC = ROOT / "public/masks/sloth"
PAGES = ROOT / "github-pages/public/masks/sloth"
VERSION = "v2"


def feathered_mouth_mask(size: tuple[int, int]) -> Image.Image:
    # One joined region: the wide upper lobe fully repaints the old smile, while
    # the lower lobe carries the O cavity that begins on the smile's own arc.
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((505, 795, 749, 925), fill=255)
    draw.ellipse((540, 805, 714, 1012), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(14))


def tongue_free_cavity(source: Image.Image) -> tuple[Image.Image, int]:
    """Make the generated O one continuous dark cavity with no coral island.

    The connected candidate is seeded inside the mouth, so darker muzzle and
    chin pixels cannot be recolored accidentally. The native mouth rim and its
    antialiasing remain generated; only the connected interior is harmonized.
    """
    array = np.asarray(source.convert("RGB"), dtype=np.uint8).copy()
    red = array[..., 0]
    green = array[..., 1]
    blue = array[..., 2]
    yy, xx = np.mgrid[0 : array.shape[0], 0 : array.shape[1]]
    candidate = (
        (xx >= 548)
        & (xx < 704)
        # Preserve the generated upper rim and cream gap below the nose. Only
        # harmonize the interior from y=842 downward, where the coral gradient
        # could otherwise read as a detached tongue during low-weight blends.
        & (yy >= 842)
        & (yy < 990)
        & (red < 225)
        & (green < 170)
        & (blue < 125)
    )
    seed = (878, 626)
    if not candidate[seed]:
        raise RuntimeError("Sloth v2 mouth seed no longer falls inside the generated cavity")
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

    # A muted cocoa-to-burnished-cocoa gradient reads as inner-mouth depth at
    # 100%, yet remains a dark opening instead of a peach tongue at low weights.
    t = np.clip((yy.astype(np.float32) - 828.0) / 142.0, 0.0, 1.0)
    texture = (
        np.sin(xx.astype(np.float32) * 0.173)
        + np.sin(yy.astype(np.float32) * 0.137)
    ) * 2.2
    target_red = np.clip(42.0 + 38.0 * t + texture, 0, 255).astype(np.uint8)
    target_green = np.clip(16.0 + 13.0 * t + texture * 0.35, 0, 255).astype(np.uint8)
    target_blue = np.clip(10.0 + 9.0 * t + texture * 0.25, 0, 255).astype(np.uint8)
    # Recolor only the eroded/feathered interior so the ImageGen rim, highlight,
    # and antialiasing stay natural and no hard binary edge is introduced.
    blend_mask = Image.fromarray(connected.astype(np.uint8) * 255)
    blend_mask = blend_mask.filter(ImageFilter.MinFilter(7)).filter(ImageFilter.GaussianBlur(3))
    mix = np.asarray(blend_mask, dtype=np.float32)[..., None] / 255.0
    target = np.stack((target_red, target_green, target_blue), axis=2).astype(np.float32)
    blended = array.astype(np.float32) * (1.0 - mix) + target * mix
    return Image.fromarray(np.clip(np.rint(blended), 0, 255).astype(np.uint8)), int(connected.sum())


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


def mouth_metrics(image: Image.Image, neutral: Image.Image) -> dict[str, object]:
    # Runtime-space region around only the mouth; it excludes nose, blush, eyes,
    # and the brown chin fur. The threshold tracks the continuous dark opening.
    array = np.asarray(image.convert("RGBA"))
    neutral_array = np.asarray(neutral.convert("RGBA"))
    # Exclude the nose and chin fur. At this crop the closed smile and every
    # intermediate/final mouth form one connected center component.
    x0, y0, x1, y1 = (162, 252, 218, 300)
    region = array[y0:y1, x0:x1, :3]
    neutral_region = neutral_array[y0:y1, x0:x1, :3]
    luminance = (
        region[..., 0].astype(np.float32) * 0.2126
        + region[..., 1].astype(np.float32) * 0.7152
        + region[..., 2].astype(np.float32) * 0.0722
    )
    dark = luminance < 92
    found = components(dark)
    significant = [component for component in found if int(component["area"]) >= 6]
    delta = np.abs(region.astype(np.int16) - neutral_region.astype(np.int16))
    return {
        "roi_xyxy": [x0, y0, x1, y1],
        "dark_threshold_luminance_lt": 92,
        "dark_pixels": int(dark.sum()),
        "significant_dark_components": len(significant),
        "largest_dark_component": significant[0] if significant else None,
        "mean_abs_rgb_delta_from_neutral": round(float(delta.mean()), 5),
        "max_rgb_delta_from_neutral": int(delta.max()),
    }


def smoothstep(value: float) -> float:
    safe = min(1.0, max(0.0, value))
    return safe * safe * (3.0 - 2.0 * safe)


def gallery_roar_weight(progress: float) -> float:
    # RenderedMaskProof runs roarIn across .13 * 7200 ms = 936 ms, then maps
    # mouth into the production drawRenderedMask roar weight.
    roar_in = smoothstep(progress)
    mouth = 0.08 + 0.92 * roar_in
    return min(1.0, max(0.0, (mouth - 0.08) * 1.22))


def save_ramp(
    states: dict[str, Image.Image], side: int, path: Path
) -> list[dict[str, object]]:
    frames: list[Image.Image] = []
    metrics: list[dict[str, object]] = []
    neutral = states["neutral"]
    count = 24
    for index in range(count):
        progress = index / (count - 1)
        weight = gallery_roar_weight(progress)
        mixed = copy_lighter_mix(states, 0.0, weight)
        proof = on_background(mixed, "#233048")
        if side == 96:
            proof = proof.resize((96, 96), Image.Resampling.LANCZOS)
        frames.append(proof)
        measured_source = mixed if side == 380 else mixed.resize((96, 96), Image.Resampling.LANCZOS)
        metrics.append(
            {
                "frame": index,
                "time_ms": round(index * (936 / (count - 1)), 3),
                "progress": round(progress, 6),
                "production_roar_weight": round(weight, 6),
                "mean_abs_rgb_delta_from_previous_frame": (
                    0.0
                    if index == 0
                    else round(
                        float(
                            np.abs(
                                np.asarray(measured_source.convert("RGB"), dtype=np.int16)
                                - np.asarray(
                                    (
                                        copy_lighter_mix(states, 0.0, gallery_roar_weight((index - 1) / (count - 1)))
                                        if side == 380
                                        else copy_lighter_mix(
                                            states,
                                            0.0,
                                            gallery_roar_weight((index - 1) / (count - 1)),
                                        ).resize((96, 96), Image.Resampling.LANCZOS)
                                    ).convert("RGB"),
                                    dtype=np.int16,
                                )
                            ).mean()
                        ),
                        6,
                    )
                ),
            }
        )
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        # GIF delay units are 10 ms; 40 ms gives a 960 ms encoded proof, the
        # closest clean 24-frame playback to the production 936 ms ramp.
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
    generated_roar_path = AUDIT / "generated-roar-v2.png"
    generated_roar = Image.open(generated_roar_path).convert("RGB")
    if generated_roar.size != CANVAS:
        raise RuntimeError("Generated Sloth v2 roar must be 1254 x 1254")

    generated_roar, harmonized_cavity_pixels = tongue_free_cavity(generated_roar)
    harmonized_source_path = AUDIT / "generated-roar-harmonized-v2.png"
    generated_roar.save(harmonized_source_path, optimize=True)

    neutral_alpha = neutral.getchannel("A")
    neutral_rgb = neutral.convert("RGB")
    mouth_mask = feathered_mouth_mask(CANVAS)
    safe_interior = neutral_alpha.filter(ImageFilter.MinFilter(41))
    mouth_mask = ImageChops.multiply(mouth_mask, safe_interior)
    mouth_mask.save(AUDIT / "roar-localization-mask-v2.png")

    roar_rgb = Image.composite(generated_roar, neutral_rgb, mouth_mask)
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
                candidate = AUDIT / f"candidate-{state}-{side}-q{quality}-v2.webp"
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
        raise RuntimeError(f"No q94-95 Sloth v2 export met 200-350KB: {candidates}")

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

    # Native state and hostile-background evidence for the repaired export.
    native_images = [on_background(masters[state], "#edf0f5") for state in STATES]
    labeled_sheet(native_images, [f"{state} / native v2" for state in STATES], 3, CANVAS[0]).save(
        AUDIT / "native-states-v2.jpg", quality=92, optimize=True
    )
    hostile_images: list[Image.Image] = []
    hostile_labels: list[str] = []
    for background_name, background in (
        ("white", "#ffffff"),
        ("black", "#000000"),
        ("cyan", "#00dcff"),
        ("magenta", "#ff00dc"),
    ):
        for state in STATES:
            hostile_images.append(on_background(actual_380[state], background))
            hostile_labels.append(f"{state} / {background_name}")
    labeled_sheet(hostile_images, hostile_labels, 3, 380).save(AUDIT / "hostile-380-states-v2.png")

    # Exact requested production weights at both runtime and thumbnail scales.
    proof_weights = (0.0, 0.10, 0.25, 0.50, 0.75, 1.0)
    stills_380: list[Image.Image] = []
    stills_96: list[Image.Image] = []
    still_labels: list[str] = []
    weight_metrics: dict[str, object] = {}
    for weight in proof_weights:
        mixed_380 = copy_lighter_mix(actual_380, 0.0, weight)
        mixed_96 = copy_lighter_mix(actual_96, 0.0, weight)
        stills_380.append(on_background(mixed_380, "#233048"))
        stills_96.append(
            on_background(mixed_96, "#233048").resize((380, 380), Image.Resampling.NEAREST)
        )
        label = f"roar {int(weight * 100)}%"
        still_labels.append(label)
        weight_metrics[f"{weight:.2f}"] = mouth_metrics(mixed_380, actual_380["neutral"])
    labeled_sheet(stills_380, still_labels, 3, 380).save(
        AUDIT / "production-roar-weights-380-v2.png"
    )
    labeled_sheet(stills_96, [f"{label} / 96px 4x" for label in still_labels], 3, 380).save(
        AUDIT / "production-roar-weights-96-v2.png"
    )

    ramp_metrics_380 = save_ramp(actual_380, 380, AUDIT / "production-roar-ramp-936ms-380-v2.gif")
    ramp_metrics_96 = save_ramp(actual_380, 96, AUDIT / "production-roar-ramp-936ms-96-v2.gif")

    # V1/V2 critic comparison at the failure weights.
    v1_runtime = {
        state: rgba(PUBLIC / f"{state}-v1.webp").resize((380, 380), Image.Resampling.LANCZOS)
        for state in STATES
    }
    compare: list[Image.Image] = []
    compare_labels: list[str] = []
    for version, states in (("v1", v1_runtime), ("v2", actual_380)):
        for weight in (0.10, 0.25, 0.50, 0.75):
            compare.append(on_background(copy_lighter_mix(states, 0.0, weight), "#233048"))
            compare_labels.append(f"{version} / roar {int(weight * 100)}%")
    labeled_sheet(compare, compare_labels, 4, 380).save(AUDIT / "v1-v2-roar-compare-380.png")

    alpha_hashes = {
        state: hashlib.sha256(masters[state].getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }
    neutral_array = np.asarray(neutral, dtype=np.int16)
    outside = np.asarray(mouth_mask) == 0
    weight_delta_series = [
        float(weight_metrics[f"{weight:.2f}"]["mean_abs_rgb_delta_from_neutral"])
        for weight in proof_weights
    ]
    dark_pixel_series = [
        int(weight_metrics[f"{weight:.2f}"]["dark_pixels"])
        for weight in proof_weights
    ]
    manifest: dict[str, object] = {
        "animal": "sloth",
        "name": "Sleepy Sloth",
        "version": VERSION,
        "repair_scope": "roar mouth transition only; v1 neutral, blink, alpha, silhouette, and matte preserved",
        "generation_route": "one built-in ImageGen mouth-only repair from the v1 neutral target, then deterministic localization",
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
        "neutral_v1_v2_pixels_identical": bool(
            np.array_equal(np.asarray(neutral), np.asarray(masters["neutral"]))
        ),
        "blink_v1_v2_pixels_identical": bool(
            np.array_equal(np.asarray(blink), np.asarray(masters["blink"]))
        ),
        "roar_outside_localization_max_channel_delta": int(
            np.abs(np.asarray(roar, dtype=np.int16) - neutral_array)[outside].max()
        ),
        "harmonized_connected_cavity_pixels": harmonized_cavity_pixels,
        "production_weight_mouth_metrics_380": weight_metrics,
        "mouth_delta_from_neutral_monotonic": all(
            current <= following
            for current, following in zip(weight_delta_series, weight_delta_series[1:])
        ),
        "mouth_dark_area_monotonic": all(
            current <= following
            for current, following in zip(dark_pixel_series, dark_pixel_series[1:])
        ),
        "single_significant_mouth_component_all_requested_weights": all(
            int(weight_metrics[f"{weight:.2f}"]["significant_dark_components"]) == 1
            for weight in proof_weights
        ),
        "gallery_ramp": {
            "production_source_duration_ms": 936,
            "sampled_frames": 24,
            "encoded_gif_duration_ms": 960,
            "encoded_frame_duration_ms": 40,
            "curve": "smoothstep roarIn, then mouth=.08+.92*roarIn and roarWeight=clamp((mouth-.08)*1.22)",
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
    manifest["generated_roar_source"] = {
        "path": str(generated_roar_path.relative_to(ROOT)),
        "sha256": sha256(generated_roar_path),
        "harmonized_path": str(harmonized_source_path.relative_to(ROOT)),
        "harmonized_sha256": sha256(harmonized_source_path),
    }
    (AUDIT / "manifest-v2.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
