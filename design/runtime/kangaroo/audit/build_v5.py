#!/usr/bin/env python3
"""Author a single expanding kangaroo mouth from the closed-lip seat."""

from __future__ import annotations

import hashlib
import json
import shutil
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
VERSION = "v5"
CANVAS = (1254, 1254)
JAW_ROI = common.JAW_ROI
CAVITY_RGB = (64, 16, 10)
SHADOW_RGB = (70, 24, 14)
# Smile sits near y=1144. Shared top keeps mid and roar as one aperture.
CAVITY_TOP = 1136
MID_BOX = (556, CAVITY_TOP, 698, 1174)
ROAR_BOX = (548, CAVITY_TOP, 706, 1186)


def ellipse_cavity(box: tuple[int, int, int, int], blur: float) -> Image.Image:
    mask = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(mask).ellipse(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur))


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


def lower_rim_luminance(image_380: Image.Image, mid_bottom_native: int = 1174) -> float:
    """Mean luminance on the first row under the mid cavity at 380px."""
    array = np.asarray(image_380.convert("RGB"), dtype=np.float32)
    y = min(379, round(mid_bottom_native * 380 / 1254) + 1)
    row = array[y, 168:212]
    return float((0.2126 * row[:, 0] + 0.7152 * row[:, 1] + 0.0722 * row[:, 2]).mean())


def main() -> None:
    for directory in (AUDIT, ALPHA, CHROMA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    neutral = rgba(ALPHA / "neutral-v1.png")
    blink = rgba(ALPHA / "blink-v1.png")

    mid_mask = ellipse_cavity(MID_BOX, 1.4)
    roar_mask = ImageChops.lighter(mid_mask, ellipse_cavity(ROAR_BOX, 1.4))
    shadow_ring = ImageChops.subtract(roar_mask, mid_mask)
    mid_mask.save(AUDIT / "v5-mid-cavity-mask.png", optimize=True)
    roar_mask.save(AUDIT / "v5-roar-cavity-mask.png", optimize=True)
    shadow_ring.save(AUDIT / "v5-shadow-ring-mask.png", optimize=True)

    mid = paint_cavity(neutral, mid_mask)
    shadow_fill = Image.new("RGB", CANVAS, SHADOW_RGB)
    mid = Image.composite(shadow_fill, mid.convert("RGB"), shadow_ring).convert("RGBA")
    mid.putalpha(neutral.getchannel("A"))
    roar = paint_cavity(neutral, roar_mask)
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
    rim_luminance: dict[str, float] = {}
    for jaw in jaws:
        image_380 = common.helper_mix(decoded, jaw, 380)
        image_96 = common.helper_mix(decoded, jaw, 96)
        sweep_380.append(composite_over(image_380, (35, 48, 72), 380))
        sweep_96.append(
            composite_over(image_96, (235, 240, 246), 96).resize((192, 192), Image.Resampling.NEAREST)
        )
        label = f"jaw {jaw:.3f}"
        labels.append(label)
        metrics = common.jaw_metrics(image_380, 380)
        helper_metrics[f"{jaw:.3f}"] = {
            "weights_neutral_blink_mid_roar": common.helper_weights(jaw).tolist(),
            "at_380": metrics,
            "at_96": common.jaw_metrics(image_96, 96),
        }
        if jaw >= 0.5:
            rim_luminance[f"{jaw:.3f}"] = round(lower_rim_luminance(image_380), 2)
    contact_sheet(sweep_380, labels, 3, 380).save(AUDIT / f"helper-jaw-sweep-380-{VERSION}.png")
    contact_sheet(sweep_96, labels, 3, 192).save(AUDIT / f"helper-jaw-sweep-96-{VERSION}.png")
    helper_closeup_sheet(decoded, jaws).save(AUDIT / f"helper-rim-closeups-4x-{VERSION}.png")
    helper_closeup_sheet(decoded, [0.5, 0.625, 0.75, 0.875, 1.0]).save(
        AUDIT / f"helper-late-bridge-rim-closeups-4x-{VERSION}.png"
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
    manifest: dict[str, object] = {
        "animal": "kangaroo",
        "name": "Kooky Kangaroo",
        "version": VERSION,
        "v1_identity_preserved": True,
        "generation_route": (
            "deterministic v5 single-aperture repair: authored oval cavities share one top "
            "at the closed-lip seat and the same cavity RGB; no new ImageGen"
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
        "cavity_boxes": {"roar-mid": list(MID_BOX), "roar": list(ROAR_BOX)},
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "outside_jaw_roi_max_channel_delta": {
            "roar-mid": int(np.abs(np.asarray(mid, dtype=np.int16) - neutral_array)[outside].max()),
            "roar": int(np.abs(np.asarray(roar, dtype=np.int16) - neutral_array)[outside].max()),
        },
        "helper_threshold_70_components": components,
        "helper_late_lower_rim_luminance": rim_luminance,
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
        "components_t70": components,
        "late_rim_luminance": rim_luminance,
        "runtime_bytes": {state: data["runtime_bytes"] for state, data in manifest_states.items()},
    }, indent=2))


if __name__ == "__main__":
    main()
