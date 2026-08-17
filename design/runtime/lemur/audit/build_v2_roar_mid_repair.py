#!/usr/bin/env python3
"""Rebuild Loopy Lemur roar-mid without a rectangular pasted mouth patch."""

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
VERSION = "v2"


def build_clean_muzzle(neutral: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Paint out the W-smile with nearby cream muzzle, leaving the nose alone."""
    rgb = np.asarray(neutral.convert("RGB"))
    dark = np.zeros((CANVAS[1], CANVAS[0]), dtype=np.uint8)
    x0, y0, x1, y1 = (540, 960, 714, 1012)
    roi = rgb[y0:y1, x0:x1]
    score = np.max(roi, axis=2)
    dark[y0:y1, x0:x1] = np.where(score < 90, 255, 0).astype(np.uint8)
    mask = Image.fromarray(dark).filter(ImageFilter.MaxFilter(11)).filter(
        ImageFilter.GaussianBlur(3.5)
    )
    sampled = Image.new("RGB", CANVAS)
    source = neutral.convert("RGB")
    sampled.paste(source.crop((0, 28, CANVAS[0], CANVAS[1])), (0, 0))
    clean_rgb = Image.composite(sampled, source, mask)
    clean = clean_rgb.convert("RGBA")
    clean.putalpha(neutral.getchannel("A"))
    return clean, mask


def author_roar_mid(clean: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Grow a single oval cavity out of the smile line, not a rectangular paste."""
    cavity = Image.new("L", CANVAS, 0)
    draw = ImageDraw.Draw(cavity)
    draw.ellipse((572, 968, 682, 1028), fill=255)
    cavity = cavity.filter(ImageFilter.GaussianBlur(2.2))
    canvas = np.asarray(clean.convert("RGB"), dtype=np.float32)
    cavity_array = np.asarray(cavity, dtype=np.float32)[..., None] / 255.0
    yy = np.arange(CANVAS[1], dtype=np.float32)[:, None, None]
    top = np.array([28.0, 14.0, 10.0], dtype=np.float32)
    bottom = np.array([72.0, 28.0, 18.0], dtype=np.float32)
    gradient = np.clip((yy - 968.0) / 60.0, 0.0, 1.0)
    cavity_rgb = top * (1.0 - gradient) + bottom * gradient
    texture = canvas.mean(axis=2, keepdims=True) - 150.0
    cavity_rgb = np.clip(cavity_rgb + texture * 0.03, 0, 255)
    rim = cavity.filter(ImageFilter.MaxFilter(9))
    rim = ImageChops.subtract(rim, cavity).filter(ImageFilter.GaussianBlur(1.2))
    rim_array = np.asarray(rim, dtype=np.float32)[..., None] / 255.0
    shadow = np.array([86.0, 58.0, 46.0], dtype=np.float32)
    base = canvas * (1.0 - rim_array * 0.35) + shadow * (rim_array * 0.35)
    base = base * (1.0 - cavity_array) + cavity_rgb * cavity_array
    out = Image.fromarray(np.clip(np.rint(base), 0, 255).astype(np.uint8)).convert("RGBA")
    out.putalpha(clean.getchannel("A"))
    return out, cavity


def main() -> None:
    for directory in (AUDIT, CHROMA, ALPHA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    v1 = {state: rgba(ALPHA / f"{state}-v1.png") for state in STATES}
    clean, smile_mask = build_clean_muzzle(v1["neutral"])
    authored_mid, cavity = author_roar_mid(clean)
    smile_mask.save(AUDIT / "v2-smile-cleanup-mask.png", optimize=True)
    cavity.save(AUDIT / "v2-roar-mid-cavity-mask.png", optimize=True)
    clean.save(AUDIT / "v2-clean-muzzle.png", optimize=True)

    masters = {
        "neutral": v1["neutral"].copy(),
        "blink": v1["blink"].copy(),
        "roar-mid": authored_mid,
        "roar": v1["roar"].copy(),
    }
    for state, image in masters.items():
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        chroma = Image.new("RGBA", CANVAS, "#00ff00")
        chroma.alpha_composite(image)
        chroma.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    chosen_side, chosen_quality = 1254, 95
    runtime_images: dict[str, Image.Image] = {}
    runtime_bytes: dict[str, int] = {}
    for state, image in masters.items():
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        image.save(public_path, "WEBP", quality=chosen_quality, alpha_quality=100, method=6, exact=True)
        shutil.copy2(public_path, PAGES / public_path.name)
        runtime_images[state] = rgba(public_path)
        runtime_bytes[state] = public_path.stat().st_size
        if runtime_bytes[state] > 350_000:
            raise RuntimeError(f"{state} runtime is {runtime_bytes[state]} bytes")

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
    for weight in (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0):
        mix = semantic_roar_mix(runtime_images, weight)
        semantic.append(on_background(mix.resize((380, 380), Image.Resampling.LANCZOS), "#233048"))
        semantic_labels.append(f"semantic roar {weight:.3f}")
    labeled_sheet(semantic, semantic_labels, 3, 380).save(
        AUDIT / f"semantic-roar-crossfade-380-{VERSION}.png", optimize=True
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
        "generation_route": "v1 ImageGen identity preserved; roar-mid rebuilt as an authored oval cavity on a smile-cleaned muzzle, not a rectangular paste",
        "v1_preserved": True,
        "runtime_export": {"side_px": chosen_side, "quality": chosen_quality, "alpha_quality": 100, "method": 6, "exact": True},
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
        "runtime_bytes": runtime_bytes,
        "holes": {state: data["metrics"]["enclosed_fully_transparent_holes"] for state, data in manifest["states"].items()},
    }, indent=2))


if __name__ == "__main__":
    main()
