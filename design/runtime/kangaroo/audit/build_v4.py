#!/usr/bin/env python3
"""Source-preserving rim integration repair for Kooky Kangaroo v4."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import build_v2 as common
import build_v3 as v3
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
VERSION = "v4"
CANVAS = (1254, 1254)
JAW_ROI = common.JAW_ROI
CAVITY_RGB = (64, 16, 10)


def cavity_masks(image: Image.Image, y0: int, y1: int) -> tuple[Image.Image, Image.Image]:
    """Return an interior core and red-detail cleanup mask, both away from the fur rim."""
    array = np.asarray(image.convert("RGBA"))
    rgb = array[..., :3].astype(np.int16)
    alpha = array[..., 3]
    yy, xx = np.ogrid[:CANVAS[1], :CANVAS[0]]
    roi = (xx >= 520) & (xx < 730) & (yy >= y0) & (yy < y1)
    interior = (
        roi
        & (alpha > 128)
        & (rgb[..., 0] < 225)
        & (rgb[..., 1] < 120)
        & (rgb[..., 2] < 105)
    )
    red_detail = (
        roi
        & (alpha > 128)
        & (rgb[..., 0] < 225)
        & (rgb[..., 0] > rgb[..., 1] + 38)
        & (rgb[..., 1] < 92)
        & (rgb[..., 2] < 88)
    )
    core = Image.fromarray(interior.astype(np.uint8) * 255)
    # Erosion keeps the generated antialiased lip/fur boundary untouched.
    core = core.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1.0))
    cleanup = Image.fromarray(red_detail.astype(np.uint8) * 255)
    cleanup = cleanup.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.0))
    return core, cleanup


def tone_cavity(
    image: Image.Image,
    core: Image.Image,
    cleanup: Image.Image,
) -> Image.Image:
    fill = Image.new("RGB", CANVAS, CAVITY_RGB)
    mask = ImageChops.lighter(core, cleanup)
    output = Image.composite(fill, image.convert("RGB"), mask).convert("RGBA")
    output.putalpha(image.getchannel("A"))
    return output


def lower_source_mask(mid_protect: Image.Image) -> Image.Image:
    ellipse = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(ellipse).ellipse((512, 1110, 738, 1213), fill=255)
    ellipse = ellipse.filter(ImageFilter.GaussianBlur(5))
    ramp = np.zeros((CANVAS[1], CANVAS[0]), dtype=np.uint8)
    for y in range(1148, 1165):
        ramp[y, :] = round(255 * (y - 1148) / 16)
    ramp[1165:, :] = 255
    mask = ImageChops.multiply(ellipse, Image.fromarray(ramp))
    # Preserve every midpoint cavity/rim pixel in the overlap.
    return ImageChops.subtract(mask, mid_protect)


def core_protect_mask(core: Image.Image, cleanup: Image.Image) -> Image.Image:
    # Protect only the true eroded cavity interior. The generated lower lip is
    # intentionally not protected: roar must replace that lip with contiguous
    # cavity pixels rather than leave a pale seam inside the opening.
    binary = (np.asarray(core) > 128).astype(np.uint8) * 255
    return Image.fromarray(binary)


def align_compact_roar_mouth(source: Image.Image, height: int = 78) -> Image.Image:
    # Keep the authored full-mouth neighborhood but compress only its vertical
    # travel so helper interpolation reveals a narrow, continuous deepening
    # instead of a large light lower bowl.
    crop = source.crop((520, 1060, 725, 1200))
    crop = crop.resize((185, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.alpha_composite(crop, (532, 1112))
    return canvas


def helper_closeup_sheet(
    decoded: dict[str, Image.Image],
    jaws: list[float],
) -> Image.Image:
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
    neutral = rgba(ALPHA / "neutral-v1.png")
    blink = rgba(ALPHA / "blink-v1.png")
    mid_source = rgba(AUDIT / "extracted-roar-mid-v3.png")
    roar_source = rgba(AUDIT / "extracted-roar-v3.png")

    # Restore the authored generated midpoint and retain its complete natural rim.
    mid_mask = v3.mid_localization_mask()
    mid = common.alpha_localize(neutral, mid_source, mid_mask)
    mid_core, mid_cleanup = cavity_masks(mid, 1141, 1180)
    mid = tone_cavity(mid, mid_core, mid_cleanup)
    mid = common.force_outside_jaw_to_neutral(mid, neutral)
    mid_protect = core_protect_mask(mid_core, mid_cleanup)

    # Pre-open most of the later cavity using the same authored roar source.
    # This keeps the selected midpoint shallow while ensuring the helper never
    # blends bright muzzle fur into a large dark semicircle after jaw .5.
    aligned_mid_lower = align_compact_roar_mouth(roar_source, 72)
    mid_lower_core, mid_lower_cleanup = cavity_masks(aligned_mid_lower, 1141, 1200)
    aligned_mid_lower = tone_cavity(aligned_mid_lower, mid_lower_core, mid_lower_cleanup)
    mid_lower_mask = lower_source_mask(mid_protect)
    mid = common.alpha_localize(mid, aligned_mid_lower, mid_lower_mask)
    expanded_mid_core, expanded_mid_cleanup = cavity_masks(mid, 1141, 1200)
    expanded_mid_tone = ImageChops.subtract(
        ImageChops.lighter(expanded_mid_core, expanded_mid_cleanup), mid_protect
    )
    fill = Image.new("RGB", CANVAS, CAVITY_RGB)
    mid = Image.composite(fill, mid.convert("RGB"), expanded_mid_tone).convert("RGBA")
    mid.putalpha(neutral.getchannel("A"))
    mid = common.force_outside_jaw_to_neutral(mid, neutral)
    mid_core, mid_cleanup = cavity_masks(mid, 1141, 1200)
    mid_protect = core_protect_mask(mid_core, mid_cleanup)

    # Use the authored full-roar lower neighborhood, normalized to the same cavity material.
    aligned_roar = align_compact_roar_mouth(roar_source, 78)
    roar_core, roar_cleanup = cavity_masks(aligned_roar, 1141, 1210)
    aligned_roar = tone_cavity(aligned_roar, roar_core, roar_cleanup)
    lower_mask = lower_source_mask(mid_protect)
    roar = common.alpha_localize(mid, aligned_roar, lower_mask)

    # Normalize only the extension, explicitly excluding every midpoint cavity pixel.
    final_core, final_cleanup = cavity_masks(roar, 1141, 1210)
    extension_tone = ImageChops.subtract(
        ImageChops.lighter(final_core, final_cleanup), mid_protect
    )
    fill = Image.new("RGB", CANVAS, CAVITY_RGB)
    roar = Image.composite(fill, roar.convert("RGB"), extension_tone).convert("RGBA")
    roar.putalpha(neutral.getchannel("A"))
    roar = common.force_outside_jaw_to_neutral(roar, neutral)

    states = {"neutral": neutral, "blink": blink, "roar-mid": mid, "roar": roar}
    neutral_alpha = neutral.getchannel("A")
    for state in ("roar-mid", "roar"):
        states[state].putalpha(neutral_alpha)

    mid_mask.save(AUDIT / "v4-mid-localization-mask.png", optimize=True)
    mid_core.save(AUDIT / "v4-mid-cavity-core-mask.png", optimize=True)
    mid_cleanup.save(AUDIT / "v4-mid-red-detail-cleanup-mask.png", optimize=True)
    mid_protect.save(AUDIT / "v4-mid-cavity-protect-mask.png", optimize=True)
    aligned_roar.save(AUDIT / "v4-aligned-generated-roar-mouth.png", optimize=True)
    lower_mask.save(AUDIT / "v4-lower-source-localization-mask.png", optimize=True)
    extension_tone.save(AUDIT / "v4-extension-tone-mask.png", optimize=True)

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
    contact_sheet(state_images, state_labels, 4, 380).save(AUDIT / "states-380-and-96-v4.png")

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
    contact_sheet(sweep_380, labels, 3, 380).save(AUDIT / "helper-jaw-sweep-380-v4.png")
    contact_sheet(sweep_96, labels, 3, 192).save(AUDIT / "helper-jaw-sweep-96-v4.png")
    helper_closeup_sheet(decoded, jaws).save(AUDIT / "helper-rim-closeups-4x-v4.png")
    helper_closeup_sheet(decoded, [0.5, 0.625, 0.75, 0.875, 1.0]).save(
        AUDIT / "helper-late-bridge-rim-closeups-4x-v4.png"
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
    contact_sheet(hostile, hostile_labels, 4, 380).save(AUDIT / "hostile-380-states-v4.png")

    alpha_hashes = {
        state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
        for state, image in states.items()
    }
    neutral_array = np.asarray(neutral, dtype=np.int16)
    outside = np.ones((CANVAS[1], CANVAS[0]), dtype=bool)
    x0, y0, x1, y1 = JAW_ROI
    outside[y0:y1, x0:x1] = False
    protect_array = np.asarray(mid_protect) > 0
    mid_array = np.asarray(mid, dtype=np.int16)
    roar_array = np.asarray(roar, dtype=np.int16)
    manifest: dict[str, object] = {
        "animal": "kangaroo",
        "name": "Kooky Kangaroo",
        "version": VERSION,
        "v1_v2_v3_preserved": True,
        "generation_route": (
            "deterministic source-preserving v4 repair using the authored v3 generated mouth neighborhoods; no new ImageGen"
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
            "roar-mid": int(np.abs(np.asarray(mid, dtype=np.int16) - neutral_array)[outside].max()),
            "roar": int(np.abs(np.asarray(roar, dtype=np.int16) - neutral_array)[outside].max()),
        },
        "roar_vs_mid_max_channel_delta_inside_protected_mid_cavity": int(
            np.abs(roar_array - mid_array)[protect_array].max()
        ),
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
    (AUDIT / "manifest-v4.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ANIMAL / "manifest-v4.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
