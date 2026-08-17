#!/usr/bin/env python3
"""Build Kooky Kangaroo v3 from authored ImageGen mouth edits."""

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
VERSION = "v3"
CANVAS = (1254, 1254)
JAW_ROI = common.JAW_ROI
CAVITY_RGB = (58, 22, 18)


def mid_localization_mask() -> Image.Image:
    mask = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(mask).ellipse((505, 1072, 744, 1192), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(8))
    protect = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(protect).ellipse((535, 972, 714, 1105), fill=255)
    protect = protect.filter(ImageFilter.GaussianBlur(3))
    return ImageChops.subtract(mask, protect)


def cavity_mask(image: Image.Image, y0: int, y1: int) -> Image.Image:
    array = np.asarray(image.convert("RGBA"))
    rgb = array[..., :3].astype(np.int16)
    alpha = array[..., 3]
    yy, xx = np.ogrid[:CANVAS[1], :CANVAS[0]]
    roi = (xx >= 520) & (xx < 730) & (yy >= y0) & (yy < y1)
    interior = (
        roi
        & (alpha > 96)
        & (rgb[..., 0] < 230)
        & (rgb[..., 1] < 125)
        & (rgb[..., 2] < 110)
    )
    mask = Image.fromarray(interior.astype(np.uint8) * 255)
    return mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))


def paint_uniform_cavity(image: Image.Image, mask: Image.Image) -> Image.Image:
    fill = Image.new("RGB", CANVAS, CAVITY_RGB)
    output = Image.composite(fill, image.convert("RGB"), mask).convert("RGBA")
    output.putalpha(image.getchannel("A"))
    return output


def align_roar_mouth(source: Image.Image) -> Image.Image:
    # The authored roar globally drifted, but its lower mouth is retained and
    # resized into the selected mid's coordinates. Final identity comes only
    # from the accepted neutral/mid state.
    crop = source.crop((520, 1060, 725, 1200))
    crop = crop.resize((185, 95), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.alpha_composite(crop, (532, 1112))
    return canvas


def lower_roar_localization_mask() -> Image.Image:
    ellipse = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(ellipse).ellipse((515, 1110, 735, 1212), fill=255)
    ellipse = ellipse.filter(ImageFilter.GaussianBlur(5))
    ramp = np.zeros((CANVAS[1], CANVAS[0]), dtype=np.uint8)
    for y in range(1138, 1156):
        ramp[y, :] = round(255 * (y - 1138) / 17)
    ramp[1156:, :] = 255
    return ImageChops.multiply(ellipse, Image.fromarray(ramp))


def force_outside_roi(image: Image.Image, neutral: Image.Image) -> Image.Image:
    return common.force_outside_jaw_to_neutral(image, neutral)


def main() -> None:
    neutral = rgba(ALPHA / "neutral-v1.png")
    blink = rgba(ALPHA / "blink-v1.png")
    mid_source = rgba(AUDIT / "extracted-roar-mid-v3.png")
    roar_source = rgba(AUDIT / "extracted-roar-v3.png")

    mid_mask = mid_localization_mask()
    mid = common.alpha_localize(neutral, mid_source, mid_mask)
    mid_cavity = cavity_mask(mid, 1120, 1182)
    mid = paint_uniform_cavity(mid, mid_cavity)
    mid = force_outside_roi(mid, neutral)

    aligned_roar = align_roar_mouth(roar_source)
    aligned_roar_cavity = cavity_mask(aligned_roar, 1120, 1210)
    aligned_roar = paint_uniform_cavity(aligned_roar, aligned_roar_cavity)
    lower_mask = lower_roar_localization_mask()
    roar = common.alpha_localize(mid, aligned_roar, lower_mask)
    roar_cavity = cavity_mask(roar, 1120, 1210)
    roar = paint_uniform_cavity(roar, roar_cavity)
    roar = force_outside_roi(roar, neutral)

    neutral_alpha = neutral.getchannel("A")
    states = {"neutral": neutral, "blink": blink, "roar-mid": mid, "roar": roar}
    for state in ("roar-mid", "roar"):
        states[state].putalpha(neutral_alpha)

    mid_mask.save(AUDIT / "v3-mid-localization-mask.png", optimize=True)
    mid_cavity.save(AUDIT / "v3-mid-cavity-tone-mask.png", optimize=True)
    aligned_roar.save(AUDIT / "v3-aligned-generated-roar-mouth.png", optimize=True)
    aligned_roar_cavity.save(AUDIT / "v3-aligned-roar-cavity-tone-mask.png", optimize=True)
    lower_mask.save(AUDIT / "v3-lower-roar-localization-mask.png", optimize=True)
    roar_cavity.save(AUDIT / "v3-final-roar-cavity-tone-mask.png", optimize=True)

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
    contact_sheet(state_images, state_labels, 4, 380).save(AUDIT / "states-380-and-96-v3.png")

    helper_metrics: dict[str, object] = {}
    sweep_380: list[Image.Image] = []
    sweep_96: list[Image.Image] = []
    labels: list[str] = []
    for index in range(9):
        jaw = index / 8
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
    contact_sheet(sweep_380, labels, 3, 380).save(AUDIT / "helper-jaw-sweep-380-v3.png")
    contact_sheet(sweep_96, labels, 3, 192).save(AUDIT / "helper-jaw-sweep-96-v3.png")

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
    contact_sheet(hostile, hostile_labels, 4, 380).save(AUDIT / "hostile-380-states-v3.png")

    alpha_hashes = {
        state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
        for state, image in states.items()
    }
    neutral_array = np.asarray(neutral, dtype=np.int16)
    outside = np.ones((CANVAS[1], CANVAS[0]), dtype=bool)
    x0, y0, x1, y1 = JAW_ROI
    outside[y0:y1, x0:x1] = False
    manifest: dict[str, object] = {
        "animal": "kangaroo",
        "name": "Kooky Kangaroo",
        "version": VERSION,
        "v1_v2_preserved": True,
        "generation_route": (
            "built-in ImageGen v3 mid edited from accepted neutral as sole target; built-in ImageGen v3 roar edited from selected mid as sole target; "
            "authored mouths localized jaw-only with the exact mid upper rim retained in final roar"
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
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "outside_jaw_roi_max_channel_delta": {
            "roar-mid": int(
                np.abs(np.asarray(mid, dtype=np.int16) - neutral_array)[outside].max()
            ),
            "roar": int(
                np.abs(np.asarray(roar, dtype=np.int16) - neutral_array)[outside].max()
            ),
        },
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
    (AUDIT / "manifest-v3.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ANIMAL / "manifest-v3.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
