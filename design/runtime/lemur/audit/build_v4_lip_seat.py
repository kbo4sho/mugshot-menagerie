#!/usr/bin/env python3
"""v4: roar-mid darkens the closed W; roar is a clearly larger aperture from that seat."""

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
VERSION = "v4"
CAVITY_RGB = (32, 16, 12)
ROAR_BOX = (536, 978, 704, 1052)


def smile_slit(neutral: Image.Image) -> Image.Image:
    array = np.asarray(neutral.convert("RGBA"))
    rgb = array[..., :3]
    alpha = array[..., 3]
    yy, xx = np.ogrid[:CANVAS[1], :CANVAS[0]]
    roi = (xx >= 552) & (xx < 692) & (yy >= 976) & (yy < 994) & (alpha > 128)
    stroke = roi & (rgb.max(axis=2) < 80)
    mask = Image.fromarray(stroke.astype(np.uint8) * 255)
    return mask.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(1.0))


def ellipse_cavity(box: tuple[int, int, int, int], blur: float) -> Image.Image:
    mask = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(mask).ellipse(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def paint(base: Image.Image, mask: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    fill = Image.new("RGB", CANVAS, color)
    output = Image.composite(fill, base.convert("RGB"), mask).convert("RGBA")
    output.putalpha(base.getchannel("A"))
    return output


def new_dark_px(before: Image.Image, after: Image.Image, threshold: int = 70) -> int:
    a = np.asarray(before.convert("RGB"))
    b = np.asarray(after.convert("RGB"))
    before_dark = a.max(axis=2) < threshold
    after_dark = b.max(axis=2) < threshold
    return int((after_dark & ~before_dark).sum())


def main() -> None:
    for directory in (AUDIT, CHROMA, ALPHA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    neutral = rgba(ALPHA / "neutral-v2.png")
    blink = rgba(ALPHA / "blink-v2.png")

    mid_mask = smile_slit(neutral)
    roar_mask = ImageChops.lighter(mid_mask, ellipse_cavity(ROAR_BOX, 1.3))
    mid_mask.save(AUDIT / "v4-mid-cavity-mask.png", optimize=True)
    roar_mask.save(AUDIT / "v4-roar-cavity-mask.png", optimize=True)

    mid = paint(neutral, mid_mask, CAVITY_RGB)
    roar = paint(neutral, roar_mask, CAVITY_RGB)

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
    for weight in (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0):
        mix = semantic_roar_mix(runtime_images, weight)
        full = on_background(mix.resize((380, 380), Image.Resampling.LANCZOS), "#233048")
        semantic.append(full)
        semantic_labels.append(f"semantic roar {weight:.3f}")
        crop = full.crop((130, 250, 250, 350)).resize((360, 300), Image.Resampling.NEAREST)
        muzzle_crops.append(crop)
        muzzle_labels.append(f"muzzle {weight:.3f}")
        if weight in (0.125, 0.25, 0.375):
            early.append(crop)
            early_labels.append(f"early {weight:.3f}")
    labeled_sheet(semantic, semantic_labels, 3, 380).save(
        AUDIT / f"semantic-roar-crossfade-380-{VERSION}.png", optimize=True
    )
    labeled_sheet(muzzle_crops, muzzle_labels, 3, 360).save(
        AUDIT / f"semantic-roar-muzzle-crops-{VERSION}.png", optimize=True
    )
    labeled_sheet(early, early_labels, 3, 360).save(
        AUDIT / f"semantic-roar-early-muzzle-crops-{VERSION}.png", optimize=True
    )

    canonical = [canonical_overlay(runtime_images[state]) for state in STATES]
    labeled_sheet(canonical, [f"{state} / canonical" for state in STATES], 4, 380).save(
        AUDIT / f"canonical-coverage-380-{VERSION}.png", optimize=True
    )

    alpha_hashes = {
        state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
        for state, image in masters.items()
    }
    mid_new = new_dark_px(neutral, mid)
    roar_new = new_dark_px(neutral, roar)
    roar_vs_mid = new_dark_px(mid, roar)
    manifest = {
        "animal": "lemur",
        "name": "Ringtail Lemur",
        "version": VERSION,
        "generation_route": (
            "v1/v2 ImageGen identity preserved; roar-mid darkens the closed W-stroke; "
            "roar is a clearly larger oval grown from that seat; no new ImageGen"
        ),
        "runtime_export": {"side_px": 1254, "quality": 95, "alpha_quality": 100, "method": 6, "exact": True},
        "cavity_rgb": list(CAVITY_RGB),
        "roar_box": list(ROAR_BOX),
        "new_dark_px_threshold_70": {
            "roar-mid_vs_neutral": mid_new,
            "roar_vs_neutral": roar_new,
            "roar_vs_roar-mid": roar_vs_mid,
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
        "new_dark_px": manifest["new_dark_px_threshold_70"],
        "runtime_bytes": runtime_bytes,
    }, indent=2))


if __name__ == "__main__":
    main()
