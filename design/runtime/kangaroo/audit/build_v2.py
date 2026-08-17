#!/usr/bin/env python3
"""Build and audit Kooky Kangaroo v2 jaw topology without touching v1."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from export_and_audit import (
    alpha_metrics,
    chroma_metrics,
    composite_over,
    contact_sheet,
    exact_green_chroma,
    fit_square,
    rgba,
    sha256,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rendered_mask_blend import mix_rendered_mask_images


ROOT = Path(__file__).resolve().parents[4]
ANIMAL = ROOT / "design/runtime/kangaroo"
AUDIT = ANIMAL / "audit"
ALPHA = ANIMAL / "alpha"
CHROMA = ANIMAL / "chroma"
PUBLIC = ROOT / "public/masks/kangaroo"
PAGES = ROOT / "github-pages/public/masks/kangaroo"
STATES = ("neutral", "blink", "roar-mid", "roar")
VERSION = "v2"
CANVAS = (1254, 1254)
JAW_ROI = (510, 1080, 740, 1212)
JAW_METRIC_ROI = (530, 1115, 720, 1212)
CAVITY_RGB = (64, 24, 18)


def ellipse_mask(
    size: tuple[int, int], box: tuple[int, int, int, int], blur: float
) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def alpha_localize(base: Image.Image, source: Image.Image, mask: Image.Image) -> Image.Image:
    valid = ImageChops.multiply(mask, source.getchannel("A"))
    output = Image.composite(source.convert("RGB"), base.convert("RGB"), valid).convert("RGBA")
    output.putalpha(base.getchannel("A"))
    return output


def remove_vertical_connector(image: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Replace the nose-to-mouth stem with horizontally sampled muzzle fur."""
    array = np.asarray(image.convert("RGBA")).copy()
    patch = array.copy()
    left_x, right_x = 601, 649
    x0, x1 = 611, 638
    for y in range(1098, 1135):
        left = array[y, left_x, :3].astype(np.float32)
        right = array[y, right_x, :3].astype(np.float32)
        for x in range(x0, x1):
            t = (x - x0) / max(x1 - x0 - 1, 1)
            patch[y, x, :3] = np.rint(left * (1 - t) + right * t).astype(np.uint8)
    patch_image = Image.fromarray(patch)
    mask = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(mask).rounded_rectangle((611, 1102, 637, 1131), radius=8, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2.2))
    output = Image.composite(patch_image, image, mask)
    output.putalpha(image.getchannel("A"))
    return output, mask


def source_cavity_mask(image: Image.Image) -> Image.Image:
    array = np.asarray(image.convert("RGBA"))
    rgb = array[..., :3].astype(np.int16)
    alpha = array[..., 3]
    yy, xx = np.ogrid[:CANVAS[1], :CANVAS[0]]
    roi = (xx >= 535) & (xx < 715) & (yy >= 1126) & (yy < 1170)
    dark = (
        roi
        & (alpha > 128)
        & (rgb[..., 0] < 185)
        & (rgb[..., 1] < 115)
        & (rgb[..., 2] < 95)
    )
    mask = Image.fromarray(dark.astype(np.uint8) * 255)
    return mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.0))


def roar_extension_mask() -> Image.Image:
    """Extend only below the shared mid-mouth upper rim."""
    scale = 4
    large = Image.new("L", (CANVAS[0] * scale, CANVAS[1] * scale), 0)
    draw = ImageDraw.Draw(large)
    draw.ellipse(tuple(value * scale for value in (552, 1114, 697, 1197)), fill=255)
    draw.rectangle((0, 0, CANVAS[0] * scale, 1134 * scale), fill=0)
    return large.resize(CANVAS, Image.Resampling.LANCZOS)


def paint_cavity(base: Image.Image, mask: Image.Image) -> Image.Image:
    fill = Image.new("RGB", CANVAS, CAVITY_RGB)
    output = Image.composite(fill, base.convert("RGB"), mask).convert("RGBA")
    output.putalpha(base.getchannel("A"))
    return output


def force_outside_jaw_to_neutral(image: Image.Image, neutral: Image.Image) -> Image.Image:
    mask = Image.new("L", CANVAS, 0)
    x0, y0, x1, y1 = JAW_ROI
    ImageDraw.Draw(mask).rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
    output = Image.composite(image, neutral, mask)
    output.putalpha(neutral.getchannel("A"))
    return output


def helper_weights(jaw: float) -> np.ndarray:
    if jaw <= 0.5:
        mid = jaw * 2
        return np.array([1 - mid, 0, mid, 0], dtype=np.float32)
    end = (jaw - 0.5) * 2
    return np.array([0, 0, 1 - end, end], dtype=np.float32)


def helper_mix(states: dict[str, Image.Image], jaw: float, side: int) -> Image.Image:
    weights = helper_weights(jaw)
    fitted = {state: fit_square(states[state], side) for state in STATES}
    return mix_rendered_mask_images(fitted, {
        "neutral": float(weights[0]),
        "blink": float(weights[1]),
        "roar-mid": float(weights[2]),
        "roar": float(weights[3]),
    })


def component_stats(mask: np.ndarray) -> tuple[int, int, list[int] | None]:
    seen = np.zeros_like(mask, dtype=bool)
    components: list[tuple[int, list[int]]] = []
    height, width = mask.shape
    for y, x in zip(*np.where(mask & ~seen)):
        if seen[y, x]:
            continue
        queue: deque[tuple[int, int]] = deque([(int(y), int(x))])
        seen[y, x] = True
        pixels: list[tuple[int, int]] = []
        while queue:
            cy, cx = queue.popleft()
            pixels.append((cy, cx))
            for dy, dx in (
                (-1, -1), (-1, 0), (-1, 1), (0, -1),
                (0, 1), (1, -1), (1, 0), (1, 1),
            ):
                ny, nx = cy + dy, cx + dx
                if (
                    0 <= ny < height
                    and 0 <= nx < width
                    and mask[ny, nx]
                    and not seen[ny, nx]
                ):
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        ys = [pixel[0] for pixel in pixels]
        xs = [pixel[1] for pixel in pixels]
        components.append((len(pixels), [min(xs), min(ys), max(xs) + 1, max(ys) + 1]))
    significant = [item for item in components if item[0] >= 3]
    if not significant:
        return 0, 0, None
    largest = max(significant, key=lambda item: item[0])
    return len(significant), largest[0], largest[1]


def jaw_metrics(image: Image.Image, side: int) -> dict[str, object]:
    array = np.asarray(image.convert("RGBA"))
    scale = side / 1254
    x0, y0, x1, y1 = [round(value * scale) for value in JAW_METRIC_ROI]
    roi = array[y0:y1, x0:x1]
    luminance = (
        0.2126 * roi[..., 0] + 0.7152 * roi[..., 1] + 0.0722 * roi[..., 2]
    )
    result: dict[str, object] = {"jaw_roi_xyxy": [x0, y0, x1, y1]}
    for threshold in (70, 100, 140):
        mask = (luminance < threshold) & (roi[..., 3] > 128)
        count, area, bbox = component_stats(mask)
        result[f"threshold_{threshold}"] = {
            "significant_components": count,
            "largest_area_px": area,
            "largest_bbox_local_xyxy": bbox,
        }
    return result


def main() -> None:
    neutral = rgba(ALPHA / "neutral-v1.png")
    blink = rgba(ALPHA / "blink-v1.png")
    mid_source = rgba(AUDIT / "extracted-roar-mid-v2.png")

    mouth_localization = ellipse_mask(CANVAS, (520, 1090, 730, 1184), 8)
    mid = alpha_localize(neutral, mid_source, mouth_localization)
    mid, connector_mask = remove_vertical_connector(mid)
    mid_cavity = source_cavity_mask(mid)
    mid = paint_cavity(mid, mid_cavity)

    extension = roar_extension_mask()
    roar_cavity = ImageChops.lighter(mid_cavity, extension)
    roar = paint_cavity(mid, roar_cavity)
    mid = force_outside_jaw_to_neutral(mid, neutral)
    roar = force_outside_jaw_to_neutral(roar, neutral)

    # State changes are strictly jaw-local, and all four mattes are the exact v1 neutral matte.
    neutral_alpha = neutral.getchannel("A")
    states = {"neutral": neutral, "blink": blink, "roar-mid": mid, "roar": roar}
    for state in ("roar-mid", "roar"):
        states[state].putalpha(neutral_alpha)

    mouth_localization.save(AUDIT / "v2-mouth-localization-mask.png", optimize=True)
    connector_mask.save(AUDIT / "v2-connector-removal-mask.png", optimize=True)
    mid_cavity.save(AUDIT / "v2-mid-cavity-mask.png", optimize=True)
    roar_cavity.save(AUDIT / "v2-roar-cavity-mask.png", optimize=True)

    for state, image in states.items():
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        exact_green_chroma(image).save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    for state, image in states.items():
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
    contact_sheet(state_images, state_labels, 4, 380).save(AUDIT / "states-380-and-96-v2.png")

    jaws = [index / 8 for index in range(9)]
    helper_metrics: dict[str, object] = {}
    sweep_380: list[Image.Image] = []
    sweep_96: list[Image.Image] = []
    labels = []
    for jaw in jaws:
        image_380 = helper_mix(decoded, jaw, 380)
        image_96 = helper_mix(decoded, jaw, 96)
        sweep_380.append(composite_over(image_380, (35, 48, 72), 380))
        sweep_96.append(
            composite_over(image_96, (235, 240, 246), 96).resize((192, 192), Image.Resampling.NEAREST)
        )
        label = f"jaw {jaw:.3f}"
        labels.append(label)
        helper_metrics[f"{jaw:.3f}"] = {
            "weights_neutral_blink_mid_roar": helper_weights(jaw).tolist(),
            "at_380": jaw_metrics(image_380, 380),
            "at_96": jaw_metrics(image_96, 96),
        }
    contact_sheet(sweep_380, labels, 3, 380).save(AUDIT / "helper-jaw-sweep-380-v2.png")
    contact_sheet(sweep_96, labels, 3, 192).save(AUDIT / "helper-jaw-sweep-96-v2.png")

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
    contact_sheet(hostile, hostile_labels, 4, 380).save(AUDIT / "hostile-380-states-v2.png")

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
        "v1_preserved": True,
        "generation_route": (
            "v1 neutral and blink preserved; built-in ImageGen supplied a v2 shallow-mouth source; "
            "roar-mid localized jaw-only, then roar deterministically extended downward from the exact same upper rim"
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
        "neutral_v1_v2_alpha_pixels_identical": (
            np.array_equal(np.asarray(neutral_alpha), np.asarray(states["neutral"].getchannel("A")))
        ),
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
    (AUDIT / "manifest-v2.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ANIMAL / "manifest-v2.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
