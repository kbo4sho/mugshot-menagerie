#!/usr/bin/env python3
"""v5: grow one cavity down from the smile rim so blends cannot keep a closed W."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from build_export_audit import (
    CANVAS,
    alpha_metrics,
    canonical_overlay,
    checker,
    labeled_sheet,
    on_background,
    rgba,
    semantic_roar_mix,
    sha256,
)


ROOT = Path(__file__).resolve().parents[4]
ANIMAL = ROOT / "design/runtime/lemur"
AUDIT = ANIMAL / "audit"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
PUBLIC = ROOT / "public/masks/lemur"
PAGES = ROOT / "github-pages/public/masks/lemur"
STATES = ("neutral", "blink", "roar-mid", "roar")
VERSION = "v5"
CAVITY_RGB = (32, 16, 12)
X_LEFT, X_RIGHT = 576, 666
SMILE_Y0, SMILE_Y1 = 978, 996
CHIN_LIMIT = 1064
MID_DEPTH, MID_EDGE = 22.0, 8.0
ROAR_DEPTH, ROAR_EDGE = 50.0, 14.0
CREAM_SHIFT = 18


def smile_component(neutral: Image.Image) -> np.ndarray:
    array = np.asarray(neutral.convert("RGB"))
    score = array.max(axis=2)
    smile = np.zeros((CANVAS[1], CANVAS[0]), dtype=bool)
    smile[SMILE_Y0:SMILE_Y1, 552:692] = score[SMILE_Y0:SMILE_Y1, 552:692] < 80
    return smile


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
    upper_array = np.maximum(smooth_curve(upper, 4), float(SMILE_Y0))
    t = np.abs((xs.astype(np.float64) - xs.mean()) / ((X_RIGHT - X_LEFT) / 2.0))
    depth = edge_depth + (center_depth - edge_depth) * np.power(np.clip(1.0 - t * t, 0, 1), 0.72)
    lower_array = np.minimum(upper_array + depth, CHIN_LIMIT)

    polygon: list[tuple[float, float]] = [
        (float(x), float(y - 1.5)) for x, y in zip(xs, upper_array)
    ]
    polygon.extend((float(x), float(y)) for x, y in zip(xs[::-1], lower_array[::-1]))
    hard = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(hard).polygon(polygon, fill=255)
    return hard.filter(ImageFilter.GaussianBlur(1.35)), upper_array.tolist(), lower_array.tolist()


def erase_smile_wings(neutral: Image.Image, smile: np.ndarray) -> tuple[Image.Image, Image.Image]:
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


def paint(base: Image.Image, mask: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    fill = Image.new("RGB", CANVAS, color)
    output = Image.composite(fill, base.convert("RGB"), mask).convert("RGBA")
    output.putalpha(base.getchannel("A"))
    return output


def new_dark_px(before: Image.Image, after: Image.Image, threshold: int = 70) -> int:
    a = np.asarray(before.convert("RGB"))
    b = np.asarray(after.convert("RGB"))
    return int(((b.max(axis=2) < threshold) & ~(a.max(axis=2) < threshold)).sum())


def muzzle_4x(mix: Image.Image) -> Image.Image:
    full = on_background(mix.resize((380, 380), Image.Resampling.LANCZOS), "#233048")
    return full.crop((130, 250, 250, 350)).resize((480, 400), Image.Resampling.NEAREST)


def main() -> None:
    for directory in (AUDIT, CHROMA, ALPHA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    neutral = rgba(ALPHA / "neutral-v2.png")
    blink = rgba(ALPHA / "blink-v2.png")
    smile = smile_component(neutral)
    base, side_mask = erase_smile_wings(neutral, smile)

    mid_mask, upper_mid, lower_mid = cavity_mask_from_smile(smile, MID_DEPTH, MID_EDGE)
    roar_mask, upper_roar, lower_roar = cavity_mask_from_smile(smile, ROAR_DEPTH, ROAR_EDGE)
    if max(abs(a - b) for a, b in zip(upper_mid, upper_roar)) > 1e-8:
        raise RuntimeError("Mid and roar upper rims diverged")

    Image.fromarray(smile.astype(np.uint8) * 255).save(AUDIT / "v5-accepted-smile.png", optimize=True)
    mid_mask.save(AUDIT / "v5-mid-cavity-mask.png", optimize=True)
    roar_mask.save(AUDIT / "v5-roar-cavity-mask.png", optimize=True)
    side_mask.save(AUDIT / "v5-smile-wing-erase-mask.png", optimize=True)

    mid = paint(base, mid_mask, CAVITY_RGB)
    roar = paint(base, roar_mask, CAVITY_RGB)

    masters = {"neutral": neutral, "blink": blink, "roar-mid": mid, "roar": roar}
    alpha = neutral.getchannel("A")
    for state, image in masters.items():
        masters[state].putalpha(alpha)
        masters[state].save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        chroma = Image.new("RGBA", CANVAS, "#00ff00")
        chroma.alpha_composite(masters[state])
        chroma.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    runtime_images: dict[str, Image.Image] = {}
    runtime_bytes: dict[str, int] = {}
    for state, image in masters.items():
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        image.save(public_path, "WEBP", quality=95, alpha_quality=100, method=6, exact=True)
        shutil.copy2(public_path, PAGES / public_path.name)
        runtime_images[state] = rgba(public_path)
        runtime_bytes[state] = public_path.stat().st_size

    runtime_380 = {
        state: image.resize((380, 380), Image.Resampling.LANCZOS)
        for state, image in runtime_images.items()
    }
    scales: list[Image.Image] = []
    labels: list[str] = []
    for state in STATES:
        scales.append(on_background(runtime_380[state], "#eef2f6"))
        labels.append(f"{state} / 380px")
    for state in STATES:
        tiny = runtime_images[state].resize((96, 96), Image.Resampling.LANCZOS)
        scales.append(on_background(tiny, "#eef2f6").resize((380, 380), Image.Resampling.NEAREST))
        labels.append(f"{state} / 96px (4x)")
    labeled_sheet(scales, labels, 4, 380).save(AUDIT / f"native-96-380-states-{VERSION}.png", optimize=True)

    native = [on_background(masters[state], checker(CANVAS, 48)) for state in STATES]
    labeled_sheet(native, [f"{state} / native" for state in STATES], 4, CANVAS[0]).save(
        AUDIT / f"native-states-{VERSION}.jpg", quality=92, optimize=True
    )

    hostile: list[Image.Image] = []
    hostile_labels: list[str] = []
    for name, background in (
        ("white", "#ffffff"), ("black", "#000000"), ("cyan", "#00e8ff"),
        ("magenta", "#ff00dc"), ("green", "#00ff00"), ("checker", checker((380, 380))),
    ):
        for state in STATES:
            hostile.append(on_background(runtime_380[state], background))
            hostile_labels.append(f"{state} / {name}")
    labeled_sheet(hostile, hostile_labels, 4, 380).save(
        AUDIT / f"hostile-380-states-{VERSION}.png", optimize=True
    )

    semantic: list[Image.Image] = []
    semantic_labels: list[str] = []
    muzzle_crops: list[Image.Image] = []
    muzzle_labels: list[str] = []
    early: list[Image.Image] = []
    early_labels: list[str] = []
    late: list[Image.Image] = []
    late_labels: list[str] = []
    required: list[Image.Image] = []
    required_labels: list[str] = []
    for weight in (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0):
        mix = semantic_roar_mix(runtime_images, weight)
        full = on_background(mix.resize((380, 380), Image.Resampling.LANCZOS), "#233048")
        semantic.append(full)
        semantic_labels.append(f"semantic roar {weight:.3f}")
        crop = muzzle_4x(mix)
        muzzle_crops.append(crop)
        muzzle_labels.append(f"muzzle 4x {weight:.3f}")
        if weight in (0.125, 0.25, 0.375):
            early.append(crop)
            early_labels.append(f"early 4x {weight:.3f}")
        if weight in (0.625, 0.75, 0.875):
            late.append(crop)
            late_labels.append(f"late 4x {weight:.3f}")
        if weight in (0.125, 0.25, 0.375, 0.625, 0.75, 0.875):
            required.append(crop)
            required_labels.append(f"bridge 4x {weight:.3f}")
    labeled_sheet(semantic, semantic_labels, 3, 380).save(
        AUDIT / f"semantic-roar-crossfade-380-{VERSION}.png", optimize=True
    )
    labeled_sheet(muzzle_crops, muzzle_labels, 3, 480).save(
        AUDIT / f"semantic-roar-muzzle-crops-{VERSION}.png", optimize=True
    )
    labeled_sheet(early, early_labels, 3, 480).save(
        AUDIT / f"helper-early-bridge-muzzle-4x-{VERSION}.png", optimize=True
    )
    labeled_sheet(late, late_labels, 3, 480).save(
        AUDIT / f"helper-late-bridge-muzzle-4x-{VERSION}.png", optimize=True
    )
    labeled_sheet(required, required_labels, 3, 480).save(
        AUDIT / f"helper-bridge-muzzle-4x-{VERSION}.png", optimize=True
    )

    canonical = [canonical_overlay(runtime_images[state]) for state in STATES]
    labeled_sheet(canonical, [f"{state} / canonical" for state in STATES], 4, 380).save(
        AUDIT / f"canonical-coverage-380-{VERSION}.png", optimize=True
    )

    alpha_hashes = {
        state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
        for state, image in masters.items()
    }
    manifest = {
        "animal": "lemur",
        "name": "Ringtail Lemur",
        "version": VERSION,
        "generation_route": (
            "v1/v2 ImageGen identity preserved; roar-mid and roar share the smile's "
            "upper rim and grow one cocoa cavity downward; leftover W wings outside "
            "that span are filled with sampled muzzle cream; no new ImageGen"
        ),
        "runtime_export": {"side_px": 1254, "quality": 95, "alpha_quality": 100, "method": 6, "exact": True},
        "cavity_rgb": list(CAVITY_RGB),
        "cavity_geometry": {
            "x_span_native_inclusive": [X_LEFT, X_RIGHT],
            "upper_rim_native_y_min_max": [round(min(upper_mid), 3), round(max(upper_mid), 3)],
            "mid_lower_native_y_min_max": [round(min(lower_mid), 3), round(max(lower_mid), 3)],
            "roar_lower_native_y_min_max": [round(min(lower_roar), 3), round(max(lower_roar), 3)],
            "mid_center_depth": MID_DEPTH,
            "roar_center_depth": ROAR_DEPTH,
        },
        "new_dark_px_threshold_70": {
            "roar-mid_vs_neutral": new_dark_px(neutral, mid),
            "roar_vs_neutral": new_dark_px(neutral, roar),
            "roar_vs_roar-mid": new_dark_px(mid, roar),
        },
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "states": {},
    }
    for state, image in masters.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        runtime_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / runtime_path.name
        manifest["states"][state] = {
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "runtime": str(runtime_path.relative_to(ROOT)),
            "runtime_bytes": runtime_path.stat().st_size,
            "runtime_sha256": sha256(runtime_path),
            "github_pages_sha256": sha256(pages_path),
            "runtime_copies_identical": runtime_path.read_bytes() == pages_path.read_bytes(),
            "metrics": alpha_metrics(image),
        }
    (AUDIT / f"manifest-{VERSION}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "alpha_identical": manifest["alpha_pixel_hashes_identical"],
        "cavity_geometry": manifest["cavity_geometry"],
        "new_dark_px": manifest["new_dark_px_threshold_70"],
        "runtime_bytes": runtime_bytes,
    }, indent=2))


if __name__ == "__main__":
    main()
