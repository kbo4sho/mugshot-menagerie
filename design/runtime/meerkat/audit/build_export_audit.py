#!/usr/bin/env python3
"""Localize, extract, export, and audit Peekaboo Meerkat v1."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
ANIMAL = ROOT / "design/runtime/meerkat"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
AUDIT = ANIMAL / "audit"
PUBLIC = ROOT / "public/masks/meerkat"
PAGES = ROOT / "github-pages/public/masks/meerkat"
STATES = ("neutral", "blink", "roar")
VERSION = "v1"
CANVAS = (1254, 1254)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def feathered_mask(
    size: tuple[int, int],
    boxes: tuple[tuple[int, int, int, int], ...],
    blur: float,
) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for box in boxes:
        draw.ellipse(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def checker(size: tuple[int, int], cell: int = 24) -> Image.Image:
    out = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(out)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            fill = "#d8d8d8" if (x // cell + y // cell) % 2 else "#f7f7f7"
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=fill)
    return out


def on_background(foreground: Image.Image, background: Image.Image | str) -> Image.Image:
    if isinstance(background, str):
        base = Image.new("RGBA", foreground.size, background)
    else:
        base = background.convert("RGBA")
    base.alpha_composite(foreground.convert("RGBA"))
    return base.convert("RGB")


def labeled_sheet(
    images: list[Image.Image], labels: list[str], columns: int, cell: int
) -> Image.Image:
    rows = (len(images) + columns - 1) // columns
    label_height = 34
    sheet = Image.new("RGB", (columns * cell, rows * (cell + label_height)), "#1c1c22")
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(images):
        x = index % columns * cell
        y = index // columns * (cell + label_height)
        rendered = image.convert("RGB")
        if rendered.size != (cell, cell):
            rendered = rendered.resize((cell, cell), Image.Resampling.LANCZOS)
        sheet.paste(rendered, (x, y + label_height))
        draw.text((x + 10, y + 10), labels[index], fill="#f4f4f7")
    return sheet


def copy_lighter_mix(states: dict[str, Image.Image], blink: float, roar: float) -> Image.Image:
    weights = np.array(
        [(1.0 - blink) * (1.0 - roar), blink * (1.0 - roar), roar],
        dtype=np.float32,
    )
    arrays = [np.asarray(states[state].convert("RGBA"), dtype=np.float32) / 255.0 for state in STATES]
    premultiplied = [array[..., :3] * array[..., 3:4] for array in arrays]
    alpha = sum(weights[index] * arrays[index][..., 3:4] for index in range(3))
    rgbp = sum(weights[index] * premultiplied[index] for index in range(3))
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    return Image.fromarray(
        np.clip(np.rint(np.concatenate([rgb, alpha], axis=2) * 255), 0, 255).astype(np.uint8)
    )


def alpha_metrics(image: Image.Image) -> dict[str, object]:
    array = np.asarray(image.convert("RGBA"))
    alpha = array[..., 3]
    ys, xs = np.where(alpha > 8)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    pads = [bbox[0], bbox[1], image.width - bbox[2], image.height - bbox[3]]
    weights = alpha.astype(np.float64)
    total = weights.sum()
    centroid = [
        float((weights * np.arange(alpha.shape[1])[None, :]).sum() / total),
        float((weights * np.arange(alpha.shape[0])[:, None]).sum() / total),
    ]

    transparent = alpha == 0
    outside = np.zeros_like(transparent, dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    height, width = transparent.shape
    for x in range(width):
        if transparent[0, x]:
            outside[0, x] = True
            queue.append((0, x))
        if transparent[height - 1, x] and not outside[height - 1, x]:
            outside[height - 1, x] = True
            queue.append((height - 1, x))
    for y in range(height):
        if transparent[y, 0] and not outside[y, 0]:
            outside[y, 0] = True
            queue.append((y, 0))
        if transparent[y, width - 1] and not outside[y, width - 1]:
            outside[y, width - 1] = True
            queue.append((y, width - 1))
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width and transparent[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                queue.append((ny, nx))
    partial = (alpha > 0) & (alpha < 255)
    green_fringe = (
        partial
        & (array[..., 1].astype(np.int16) > array[..., 0].astype(np.int16) + 28)
        & (array[..., 1].astype(np.int16) > array[..., 2].astype(np.int16) + 28)
    )
    return {
        "dimensions": [image.width, image.height],
        "bbox_alpha_gt_8": bbox,
        "padding_px_left_top_right_bottom": pads,
        "alpha_weighted_centroid": [round(value, 3) for value in centroid],
        "transparent_corner_alpha": [
            int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])
        ],
        "partially_transparent_pixels": int(partial.sum()),
        "enclosed_fully_transparent_holes": int((transparent & ~outside).sum()),
        "green_dominant_partial_alpha_pixels": int(green_fringe.sum()),
    }


def canonical_overlay(image: Image.Image) -> Image.Image:
    out = on_background(image.resize((380, 380), Image.Resampling.LANCZOS), "#eef2f6")
    draw = ImageDraw.Draw(out)
    draw.line((190, 18, 190, 360), fill="#00b8d9", width=2)
    draw.line((20, 225, 360, 225), fill="#ff3d71", width=2)
    draw.line((20, 305, 360, 305), fill="#ff9f1c", width=3)
    draw.ellipse((112, 178, 128, 194), outline="#7b2cff", width=3)
    draw.ellipse((252, 178, 268, 194), outline="#7b2cff", width=3)
    draw.text((24, 231), "tracked origin", fill="#92204f")
    draw.text((24, 311), "standard jaw", fill="#8a5000")
    return out


def main() -> None:
    for directory in (CHROMA, ALPHA, AUDIT, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    generated_paths = {state: AUDIT / f"{state}-generated-{VERSION}.png" for state in STATES}
    generated = {state: Image.open(path).convert("RGB") for state, path in generated_paths.items()}
    if any(image.size != CANVAS for image in generated.values()):
        raise RuntimeError("All generated meerkat state sources must be 1254 x 1254")

    for state, path in generated_paths.items():
        raw = CHROMA / f"{state}-raw-{VERSION}.png"
        if not raw.exists() or raw.read_bytes() != path.read_bytes():
            shutil.copy2(path, raw)

    extracted_path = AUDIT / f"neutral-extracted-{VERSION}.png"
    helper = Path.home() / ".codex/skills/.system/imagegen/scripts/remove_chroma_key.py"
    subprocess.run(
        [
            sys.executable, str(helper), "--input", str(generated_paths["neutral"]),
            "--out", str(extracted_path), "--auto-key", "border", "--soft-matte",
            "--transparent-threshold", "12", "--opaque-threshold", "220", "--despill",
            "--edge-contract", "1", "--force",
        ],
        check=True,
    )
    neutral = rgba(extracted_path)
    neutral_alpha = neutral.getchannel("A")
    neutral_rgb = neutral.convert("RGB")

    blink_mask = feathered_mask(CANVAS, ((250, 480, 600, 850), (655, 480, 1005, 850)), blur=14)
    roar_mask = feathered_mask(
        CANVAS,
        ((240, 280, 560, 520), (690, 280, 1020, 520), (430, 860, 800, 1140)),
        blur=16,
    )
    safe_interior = neutral_alpha.filter(ImageFilter.MinFilter(31))
    masks = {
        "blink": ImageChops.multiply(blink_mask, safe_interior),
        "roar": ImageChops.multiply(roar_mask, safe_interior),
    }
    for state, mask in masks.items():
        mask.save(AUDIT / f"{state}-localization-mask-{VERSION}.png", optimize=True)

    masters: dict[str, Image.Image] = {"neutral": neutral}
    for state in ("blink", "roar"):
        localized_rgb = Image.composite(generated[state], neutral_rgb, masks[state])
        localized = localized_rgb.convert("RGBA")
        localized.putalpha(neutral_alpha)
        masters[state] = localized

    for state, image in masters.items():
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        chroma = Image.new("RGBA", CANVAS, "#00ff00")
        chroma.alpha_composite(image)
        chroma.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    candidates: dict[tuple[int, int], list[int]] = {}
    chosen_side: int | None = None
    chosen_quality: int | None = None
    for side in (1254, 1152, 1024, 896):
        for quality in (95, 94):
            sizes: list[int] = []
            for state, image in masters.items():
                runtime = image if side == 1254 else image.resize((side, side), Image.Resampling.LANCZOS)
                path = AUDIT / f"candidate-{state}-{side}-q{quality}.webp"
                runtime.save(path, "WEBP", quality=quality, alpha_quality=100, method=6, exact=True)
                sizes.append(path.stat().st_size)
            candidates[(side, quality)] = sizes
            if min(sizes) >= 200_000 and max(sizes) <= 350_000:
                chosen_side, chosen_quality = side, quality
                break
        if chosen_side is not None:
            break
    if chosen_side is None:
        for side in (1254, 1152, 1024, 896):
            for quality in (95, 94):
                if max(candidates[(side, quality)]) <= 350_000:
                    chosen_side, chosen_quality = side, quality
                    break
            if chosen_side is not None:
                break
    if chosen_side is None or chosen_quality is None:
        raise RuntimeError("No q94-95 meerkat export stayed under 350KB")

    runtime_images: dict[str, Image.Image] = {}
    for state, image in masters.items():
        runtime = image if chosen_side == 1254 else image.resize((chosen_side, chosen_side), Image.Resampling.LANCZOS)
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        runtime.save(public_path, "WEBP", quality=chosen_quality, alpha_quality=100, method=6, exact=True)
        shutil.copy2(public_path, PAGES / public_path.name)
        runtime_images[state] = rgba(public_path)

    native = [on_background(masters[state], checker(CANVAS, 48)) for state in STATES]
    labeled_sheet(native, [f"{state} / native" for state in STATES], 3, CANVAS[0]).save(
        AUDIT / f"native-states-{VERSION}.jpg", quality=92, optimize=True
    )

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
    labeled_sheet(scales, labels, 3, 380).save(AUDIT / f"native-96-380-states-{VERSION}.png", optimize=True)

    hostile: list[Image.Image] = []
    hostile_labels: list[str] = []
    for name, background in (
        ("white", "#ffffff"), ("black", "#000000"), ("cyan", "#00e8ff"),
        ("magenta", "#ff00dc"), ("green", "#00ff00"), ("checker", checker((380, 380))),
    ):
        for state in STATES:
            hostile.append(on_background(runtime_380[state], background))
            hostile_labels.append(f"{state} / {name}")
    labeled_sheet(hostile, hostile_labels, 3, 380).save(
        AUDIT / f"hostile-380-states-{VERSION}.png", optimize=True
    )

    comparison = [on_background(runtime_380["neutral"], "#eef2f6")]
    comparison_labels = ["MEERKAT: tan + dark patches"]
    for animal_id, version, label in (
        ("raccoon", "v1", "raccoon comparison"),
        ("fox", "v1", "fox comparison"),
        ("cat", "v1", "cat comparison"),
    ):
        path = ROOT / f"public/masks/{animal_id}/neutral-{version}.webp"
        if path.exists():
            other = rgba(path).resize((380, 380), Image.Resampling.LANCZOS)
            comparison.append(on_background(other, "#eef2f6"))
            comparison_labels.append(label)
    labeled_sheet(comparison, comparison_labels, len(comparison), 380).save(
        AUDIT / f"species-comparison-380-{VERSION}.png", optimize=True
    )

    canonical = [canonical_overlay(runtime_images[state]) for state in STATES]
    labeled_sheet(canonical, [f"{state} / canonical" for state in STATES], 3, 380).save(
        AUDIT / f"canonical-coverage-380-{VERSION}.png", optimize=True
    )

    mixes: list[Image.Image] = []
    mix_labels: list[str] = []
    for label, blink, roar in (
        ("neutral", 0, 0),
        ("blink 25%", .25, 0),
        ("blink 50%", .5, 0),
        ("blink 75%", .75, 0),
        ("blink 100%", 1, 0),
        ("roar 25%", 0, .25),
        ("roar 50%", 0, .5),
        ("roar 75%", 0, .75),
        ("roar 100%", 0, 1),
        ("blink 50 + roar 50", .5, .5),
    ):
        mixes.append(on_background(copy_lighter_mix(runtime_images, blink, roar).resize((380, 380), Image.Resampling.LANCZOS), "#233048"))
        mix_labels.append(label)
    labeled_sheet(mixes, mix_labels, 5, 380).save(
        AUDIT / f"copy-lighter-crossfades-380-{VERSION}.png", optimize=True
    )

    alpha_hashes = {
        state: hashlib.sha256(np.asarray(image.getchannel("A")).tobytes()).hexdigest()
        for state, image in masters.items()
    }
    neutral_array = np.asarray(masters["neutral"], dtype=np.int16)
    manifest: dict[str, object] = {
        "animal": "meerkat",
        "name": "Peekaboo Meerkat",
        "version": VERSION,
        "generation_route": "Codex ImageGen chroma sources; helper extracts the neutral silhouette; blink/roar RGB is localized onto the approved neutral and every state receives the identical alpha plane",
        "runtime_export": {
            "side_px": chosen_side,
            "quality": chosen_quality,
            "alpha_quality": 100,
            "method": 6,
            "exact": True,
        },
        "candidate_sizes_bytes": {f"{side}-q{quality}": values for (side, quality), values in candidates.items()},
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "outside_localization_max_channel_delta": {
            state: int(
                np.abs(np.asarray(masters[state], dtype=np.int16) - neutral_array)[np.asarray(masks[state]) == 0].max()
            )
            for state in ("blink", "roar")
        },
        "states": {},
    }
    for state, image in masters.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        runtime_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / runtime_path.name
        decoded = Image.open(runtime_path).convert("RGBA")
        manifest["states"][state] = {
            "generated_chroma_source": str(generated_paths[state].relative_to(ROOT)),
            "localized_chroma_master": str((CHROMA / f"{state}-{VERSION}.png").relative_to(ROOT)),
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "runtime": str(runtime_path.relative_to(ROOT)),
            "runtime_bytes": runtime_path.stat().st_size,
            "runtime_sha256": sha256(runtime_path),
            "github_pages_sha256": sha256(pages_path),
            "runtime_copies_identical": runtime_path.read_bytes() == pages_path.read_bytes(),
            "decoded_alpha_sha256": hashlib.sha256(decoded.getchannel("A").tobytes()).hexdigest(),
            "metrics": alpha_metrics(image),
        }
    (AUDIT / f"manifest-{VERSION}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "chosen": {"side": chosen_side, "quality": chosen_quality},
        "alpha_identical": manifest["alpha_pixel_hashes_identical"],
        "outside_delta": manifest["outside_localization_max_channel_delta"],
        "runtime_bytes": {state: data["runtime_bytes"] for state, data in manifest["states"].items()},
        "holes": {state: data["metrics"]["enclosed_fully_transparent_holes"] for state, data in manifest["states"].items()},
        "green_fringe": {state: data["metrics"]["green_dominant_partial_alpha_pixels"] for state, data in manifest["states"].items()},
    }, indent=2))


if __name__ == "__main__":
    main()
