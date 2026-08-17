#!/usr/bin/env python3
"""Author a single expanding lemur mouth from the closed-smile seat.

v2 still blended the generated roar face into the late half, so helper
crossfades showed a leftover W-smile plus a second, lower cavity. v3 keeps
the approved v1/v2 identity and replaces both roar states with one oval
family painted on the neutral muzzle.
"""

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
VERSION = "v3"
CAVITY_RGB = (32, 16, 12)
SHADOW_RGB = (48, 26, 20)
CAVITY_TOP = 970
MID_BOX = (548, CAVITY_TOP, 692, 1020)
ROAR_BOX = (540, CAVITY_TOP, 700, 1046)


def ellipse_cavity(box: tuple[int, int, int, int], blur: float) -> Image.Image:
    mask = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(mask).ellipse(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def paint(base: Image.Image, mask: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    fill = Image.new("RGB", CANVAS, color)
    output = Image.composite(fill, base.convert("RGB"), mask).convert("RGBA")
    output.putalpha(base.getchannel("A"))
    return output


def main() -> None:
    for directory in (AUDIT, CHROMA, ALPHA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    v2 = {state: rgba(ALPHA / f"{state}-v2.png") for state in ("neutral", "blink")}
    neutral = v2["neutral"]
    blink = v2["blink"]

    mid_mask = ellipse_cavity(MID_BOX, 1.6)
    roar_mask = ImageChops.lighter(mid_mask, ellipse_cavity(ROAR_BOX, 1.6))
    shadow_ring = ImageChops.subtract(roar_mask, mid_mask)
    mid_mask.save(AUDIT / "v3-mid-cavity-mask.png", optimize=True)
    roar_mask.save(AUDIT / "v3-roar-cavity-mask.png", optimize=True)
    shadow_ring.save(AUDIT / "v3-shadow-ring-mask.png", optimize=True)

    mid = paint(neutral, mid_mask, CAVITY_RGB)
    mid = paint(mid, shadow_ring, SHADOW_RGB)
    roar = paint(neutral, roar_mask, CAVITY_RGB)

    masters = {"neutral": neutral, "blink": blink, "roar-mid": mid, "roar": roar}
    alpha = neutral.getchannel("A")
    for state in ("roar-mid", "roar"):
        masters[state].putalpha(alpha)
        masters[state].save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        chroma = Image.new("RGBA", CANVAS, "#00ff00")
        chroma.alpha_composite(masters[state])
        chroma.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)
    for state in ("neutral", "blink"):
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
    for weight in (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0):
        mix = semantic_roar_mix(runtime_images, weight)
        full = on_background(mix.resize((380, 380), Image.Resampling.LANCZOS), "#233048")
        semantic.append(full)
        semantic_labels.append(f"semantic roar {weight:.3f}")
        crop = full.crop((130, 250, 250, 350)).resize((360, 300), Image.Resampling.NEAREST)
        muzzle_crops.append(crop)
        muzzle_labels.append(f"muzzle {weight:.3f}")
    labeled_sheet(semantic, semantic_labels, 3, 380).save(
        AUDIT / f"semantic-roar-crossfade-380-{VERSION}.png", optimize=True
    )
    labeled_sheet(muzzle_crops, muzzle_labels, 3, 360).save(
        AUDIT / f"semantic-roar-muzzle-crops-{VERSION}.png", optimize=True
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
            "v1/v2 ImageGen identity preserved; roar-mid and roar authored as one oval "
            "family on the closed-smile seat; generated roar face is not used"
        ),
        "runtime_export": {"side_px": 1254, "quality": 95, "alpha_quality": 100, "method": 6, "exact": True},
        "cavity_rgb": list(CAVITY_RGB),
        "cavity_boxes": {"roar-mid": list(MID_BOX), "roar": list(ROAR_BOX)},
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
