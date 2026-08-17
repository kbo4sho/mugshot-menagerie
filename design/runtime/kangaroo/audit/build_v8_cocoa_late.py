#!/usr/bin/env python3
"""v8: roar-mid is already cocoa through the roar opening so late lerps cannot muddy."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import build_v2 as common
from export_and_audit import (
    alpha_metrics,
    chroma_metrics,
    composite_over,
    contact_sheet,
    exact_green_chroma,
    rgba,
    sha256,
)


ROOT = Path(__file__).resolve().parents[4]
ANIMAL = ROOT / "design/runtime/kangaroo"
AUDIT = ANIMAL / "audit"
ALPHA = ANIMAL / "alpha"
CHROMA = ANIMAL / "chroma"
PUBLIC = ROOT / "public/masks/kangaroo"
PAGES = ROOT / "github-pages/public/masks/kangaroo"
STATES = ("neutral", "blink", "roar-mid", "roar")
VERSION = "v8"
CANVAS = (1254, 1254)
JAW_ROI = common.JAW_ROI
CAVITY_RGB = (64, 16, 10)
SMILE_SEED = (1137, 628)
X_LEFT, X_RIGHT = 568, 682
# Late linear mix of cream×cocoa is what lost v7. Mid and roar share the v7
# mid cocoa mask so 0.625–0.875 stay on cavity color without enlarging the
# early-bridge bowl that v6/v7 already passed.
MID_DEPTH, MID_EDGE = 28.0, 10.0
ROAR_DEPTH, ROAR_EDGE = 28.0, 10.0
CREAM_SHIFT = 22


def connected_from_seed(binary: np.ndarray, seed: tuple[int, int]) -> np.ndarray:
    if not binary[seed]:
        raise RuntimeError(f"Seed {seed} is not inside the candidate mask")
    connected = np.zeros_like(binary, dtype=bool)
    queue: deque[tuple[int, int]] = deque([seed])
    connected[seed] = True
    while queue:
        y, x = queue.popleft()
        for dy, dx in (
            (-1, -1), (-1, 0), (-1, 1), (0, -1),
            (0, 1), (1, -1), (1, 0), (1, 1),
        ):
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


def smile_component(neutral: Image.Image) -> np.ndarray:
    array = np.asarray(neutral.convert("RGB"))
    score = array.max(axis=2)
    candidate = np.zeros((CANVAS[1], CANVAS[0]), dtype=bool)
    candidate[1128:1148, 560:690] = score[1128:1148, 560:690] < 96
    return connected_from_seed(candidate, SMILE_SEED)


def smooth_curve(values: np.ndarray, radius: int = 4) -> np.ndarray:
    padded = np.pad(values, (radius, radius), mode="edge")
    kernel = np.ones(radius * 2 + 1, dtype=np.float64) / (radius * 2 + 1)
    return np.convolve(padded, kernel, mode="valid")


def cavity_mask_from_smile(
    smile: np.ndarray,
    center_depth: float,
    edge_depth: float,
) -> tuple[Image.Image, list[float], list[float]]:
    xs = np.arange(X_LEFT, X_RIGHT + 1)
    upper = np.full(xs.shape, np.nan, dtype=np.float64)
    for index, x in enumerate(xs):
        ys = np.where(smile[:, x])[0]
        if len(ys):
            upper[index] = float(ys.min())
    known = np.where(~np.isnan(upper))[0]
    if known.size < 8:
        raise RuntimeError("Accepted smile is too sparse to build an upper rim")
    missing = np.isnan(upper)
    if missing.any():
        upper[missing] = np.interp(np.where(missing)[0], known, upper[known])
    upper_array = smooth_curve(upper, 4)
    t = np.abs((xs.astype(np.float64) - xs.mean()) / ((X_RIGHT - X_LEFT) / 2.0))
    depth = edge_depth + (center_depth - edge_depth) * np.power(np.clip(1.0 - t * t, 0, 1), 0.72)
    lower_array = np.minimum(upper_array + depth, JAW_ROI[3] - 8)

    polygon: list[tuple[float, float]] = [
        (float(x), float(y - 1.5)) for x, y in zip(xs, upper_array)
    ]
    polygon.extend((float(x), float(y)) for x, y in zip(xs[::-1], lower_array[::-1]))
    hard = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(hard).polygon(polygon, fill=255)
    return hard.filter(ImageFilter.GaussianBlur(1.35)), upper_array.tolist(), lower_array.tolist()


def erase_smile_wings(neutral: Image.Image, smile: np.ndarray) -> Image.Image:
    smile_image = Image.fromarray(smile.astype(np.uint8) * 255)
    side_selector = np.ones((CANVAS[1], CANVAS[0]), dtype=np.uint8) * 255
    side_selector[:, X_LEFT : X_RIGHT + 1] = 0
    side_mask = ImageChops.multiply(
        smile_image.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(1.5)),
        Image.fromarray(side_selector),
    )
    array = np.asarray(neutral.convert("RGB"), dtype=np.uint8)
    sampled = array.copy()
    sampled[:-CREAM_SHIFT] = array[CREAM_SHIFT:]
    base = Image.composite(Image.fromarray(sampled), Image.fromarray(array), side_mask)
    output = base.convert("RGBA")
    output.putalpha(neutral.getchannel("A"))
    return output, side_mask


def paint_cavity(base: Image.Image, mask: Image.Image) -> Image.Image:
    fill = Image.new("RGB", CANVAS, CAVITY_RGB)
    output = Image.composite(fill, base.convert("RGB"), mask).convert("RGBA")
    output.putalpha(base.getchannel("A"))
    return output


def helper_closeup_sheet(decoded: dict[str, Image.Image], jaws: list[float]) -> Image.Image:
    tiles: list[Image.Image] = []
    labels: list[str] = []
    for jaw in jaws:
        mixed = common.helper_mix(decoded, jaw, 380)
        composed = composite_over(mixed, (235, 240, 246), 380)
        crop = composed.crop((145, 316, 235, 378)).resize((360, 248), Image.Resampling.LANCZOS)
        tiles.append(crop)
        labels.append(f"jaw {jaw:.3f} / rim 4x")
    return contact_sheet(tiles, labels, 3, 360)


def main() -> None:
    for directory in (AUDIT, ALPHA, CHROMA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    neutral = rgba(ALPHA / "neutral-v1.png")
    blink = rgba(ALPHA / "blink-v1.png")
    smile = smile_component(neutral)
    smile_image = Image.fromarray(smile.astype(np.uint8) * 255)
    base, side_mask = erase_smile_wings(neutral, smile)

    mid_mask, upper_mid, lower_mid = cavity_mask_from_smile(smile, MID_DEPTH, MID_EDGE)
    roar_mask, upper_roar, lower_roar = cavity_mask_from_smile(smile, ROAR_DEPTH, ROAR_EDGE)
    if max(abs(a - b) for a, b in zip(upper_mid, upper_roar)) > 1e-8:
        raise RuntimeError("Mid and roar upper rims diverged")

    mid_mask.save(AUDIT / "v8-mid-cavity-mask.png", optimize=True)
    roar_mask.save(AUDIT / "v8-roar-cavity-mask.png", optimize=True)
    side_mask.save(AUDIT / "v8-smile-wing-erase-mask.png", optimize=True)
    smile_image.save(AUDIT / "v8-accepted-smile.png", optimize=True)

    mid = paint_cavity(base, mid_mask)
    roar = paint_cavity(base, roar_mask)
    mid = common.force_outside_jaw_to_neutral(mid, neutral)
    roar = common.force_outside_jaw_to_neutral(roar, neutral)

    states = {"neutral": neutral, "blink": blink, "roar-mid": mid, "roar": roar}
    alpha = neutral.getchannel("A")
    for state in ("roar-mid", "roar"):
        states[state].putalpha(alpha)

    for state, image in states.items():
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        exact_green_chroma(image).save(CHROMA / f"{state}-{VERSION}.png", optimize=True)
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        image.save(public_path, "WEBP", quality=95, alpha_quality=100, method=6, exact=True)
        shutil.copy2(public_path, PAGES / public_path.name)

    decoded = {state: rgba(PUBLIC / f"{state}-{VERSION}.webp") for state in STATES}

    state_images: list[Image.Image] = []
    state_labels: list[str] = []
    for side in (380, 96):
        for state in STATES:
            tile = composite_over(decoded[state], (235, 240, 246), side)
            if side == 96:
                tile = tile.resize((380, 380), Image.Resampling.NEAREST)
            state_images.append(tile)
            state_labels.append(f"{state} / {side}px")
    contact_sheet(state_images, state_labels, 4, 380).save(AUDIT / f"states-380-and-96-{VERSION}.png")

    helper_metrics: dict[str, object] = {}
    sweep_380: list[Image.Image] = []
    sweep_96: list[Image.Image] = []
    labels: list[str] = []
    jaws = [index / 8 for index in range(9)]
    for jaw in jaws:
        image_380 = common.helper_mix(decoded, jaw, 380)
        image_96 = common.helper_mix(decoded, jaw, 96)
        sweep_380.append(composite_over(image_380, (35, 48, 72), 380))
        sweep_96.append(
            composite_over(image_96, (235, 240, 246), 96).resize((192, 192), Image.Resampling.NEAREST)
        )
        label = f"jaw {jaw:.3f}"
        labels.append(label)
        helper_metrics[f"{jaw:.3f}"] = {
            "weights_neutral_blink_mid_roar": common.helper_weights(jaw).tolist(),
            "at_380": common.jaw_metrics(image_380, 380),
            "at_96": common.jaw_metrics(image_96, 96),
        }
    contact_sheet(sweep_380, labels, 3, 380).save(AUDIT / f"helper-jaw-sweep-380-{VERSION}.png")
    contact_sheet(sweep_96, labels, 3, 192).save(AUDIT / f"helper-jaw-sweep-96-{VERSION}.png")
    helper_closeup_sheet(decoded, jaws).save(AUDIT / f"helper-rim-closeups-4x-{VERSION}.png")
    helper_closeup_sheet(decoded, [0.125, 0.25, 0.375]).save(
        AUDIT / f"helper-early-bridge-rim-closeups-4x-{VERSION}.png"
    )
    helper_closeup_sheet(decoded, [0.5, 0.625, 0.75, 0.875, 1.0]).save(
        AUDIT / f"helper-late-bridge-rim-closeups-4x-{VERSION}.png"
    )
    helper_closeup_sheet(decoded, [0.625, 0.75, 0.875]).save(
        AUDIT / f"helper-late-bridge-0625-0750-0875-4x-{VERSION}.png"
    )

    hostile: list[Image.Image] = []
    hostile_labels: list[str] = []
    for name, color in (
        ("white", (255, 255, 255)),
        ("black", (0, 0, 0)),
        ("cyan", (0, 220, 255)),
        ("magenta", (255, 0, 220)),
    ):
        for state in STATES:
            hostile.append(composite_over(decoded[state], color, 380))
            hostile_labels.append(f"{state} / {name}")
    contact_sheet(hostile, hostile_labels, 4, 380).save(AUDIT / f"hostile-380-states-{VERSION}.png")

    alpha_hashes = {
        state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
        for state, image in states.items()
    }
    neutral_array = np.asarray(neutral, dtype=np.int16)
    outside = np.ones((CANVAS[1], CANVAS[0]), dtype=bool)
    x0, y0, x1, y1 = JAW_ROI
    outside[y0:y1, x0:x1] = False
    components = {
        jaw: helper_metrics[f"{jaw:.3f}"]["at_380"]["threshold_70"]["significant_components"]
        for jaw in jaws
    }
    mid_arr = np.asarray(decoded["roar-mid"].convert("RGB"), dtype=np.int16)
    roar_arr = np.asarray(decoded["roar"].convert("RGB"), dtype=np.int16)
    mix_750 = np.asarray(common.helper_mix(decoded, 0.75, 1254).convert("RGB"), dtype=np.int16)
    cream_in_mid = mid_arr.max(axis=2) > 160
    cocoa_in_roar = roar_arr.max(axis=2) < 90
    late_band = cream_in_mid & cocoa_in_roar
    late_band_mean = [int(round(v)) for v in mix_750[late_band].mean(axis=0)] if late_band.any() else [64, 16, 10]
    cavity_in_both = (mid_arr.max(axis=2) < 90) & cocoa_in_roar
    mix_750_cavity_mean = [int(round(v)) for v in mix_750[cavity_in_both].mean(axis=0)] if cavity_in_both.any() else []
    manifest: dict[str, object] = {
        "animal": "kangaroo",
        "name": "Kooky Kangaroo",
        "version": VERSION,
        "v1_identity_preserved": True,
        "generation_route": (
            "deterministic v8 cocoa-late repair: roar-mid already uses the full roar "
            "cocoa mask from the smile rim so helper 0.625–0.875 cannot mix cream into "
            "cavity; leftover W wings are filled with sampled muzzle cream; no new ImageGen"
        ),
        "runtime_export": {
            "side_px": 1254,
            "quality": 95,
            "alpha_quality": 100,
            "method": 6,
            "exact": True,
        },
        "jaw_roi_native_xyxy": list(JAW_ROI),
        "cavity_rgb": list(CAVITY_RGB),
        "cavity_geometry": {
            "x_span_native_inclusive": [X_LEFT, X_RIGHT],
            "upper_rim_native_y_min_max": [round(min(upper_mid), 3), round(max(upper_mid), 3)],
            "mid_lower_native_y_min_max": [round(min(lower_mid), 3), round(max(lower_mid), 3)],
            "roar_lower_native_y_min_max": [round(min(lower_roar), 3), round(max(lower_roar), 3)],
            "mid_center_depth": MID_DEPTH,
            "roar_center_depth": ROAR_DEPTH,
        },
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "outside_jaw_roi_max_channel_delta": {
            "roar-mid": int(np.abs(np.asarray(mid, dtype=np.int16) - neutral_array)[outside].max()),
            "roar": int(np.abs(np.asarray(roar, dtype=np.int16) - neutral_array)[outside].max()),
        },
        "helper_threshold_70_components": components,
        "late_band_cream_mid_cocoa_roar_px": int(late_band.sum()),
        "jaw_0750_late_band_mean_rgb": late_band_mean,
        "jaw_0750_shared_cavity_mean_rgb": mix_750_cavity_mean,
        "helper_jaw_sweep": helper_metrics,
        "states": {},
    }
    manifest_states: dict[str, object] = {}
    for state, image in states.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        chroma_path = CHROMA / f"{state}-{VERSION}.png"
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / public_path.name
        manifest_states[state] = {
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
    (AUDIT / f"manifest-{VERSION}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ANIMAL / f"manifest-{VERSION}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "alpha_identical": manifest["alpha_pixel_hashes_identical"],
        "outside_delta": manifest["outside_jaw_roi_max_channel_delta"],
        "cavity_geometry": manifest["cavity_geometry"],
        "late_band_px": manifest["late_band_cream_mid_cocoa_roar_px"],
        "jaw_0750_late_band_mean_rgb": manifest["jaw_0750_late_band_mean_rgb"],
        "jaw_0750_shared_cavity_mean_rgb": manifest["jaw_0750_shared_cavity_mean_rgb"],
        "components_t70": components,
        "runtime_bytes": {state: data["runtime_bytes"] for state, data in manifest_states.items()},
    }, indent=2))


if __name__ == "__main__":
    main()
