#!/usr/bin/env python3
"""Export and audit the identity-locked Party Parrot v1 state pack."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[4]
PARROT = ROOT / "design/runtime/parrot"
AUDIT = PARROT / "audit"
ALPHA = PARROT / "alpha"
CHROMA = PARROT / "chroma"
PUBLIC = ROOT / "public/masks/parrot"
PAGES = ROOT / "github-pages/public/masks/parrot"
STATES = ("neutral", "blink", "roar")
VERSION = "v1"
RUNTIME_SIDE = 1344
RUNTIME_QUALITY = 95


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def checker(size: tuple[int, int], cell: int = 24) -> Image.Image:
    out = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(out)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            color = "#d8d8d8" if (x // cell + y // cell) % 2 else "#f7f7f7"
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=color)
    return out


def on_background(foreground: Image.Image, background: Image.Image | str) -> Image.Image:
    base = (
        Image.new("RGBA", foreground.size, background)
        if isinstance(background, str)
        else background.convert("RGBA")
    )
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
        sheet.paste(image.convert("RGB"), (x, y + label_height))
        draw.text((x + 10, y + 10), labels[index], fill="#f4f4f7")
    return sheet


def copy_lighter_mix(
    states: dict[str, Image.Image], blink_weight: float, roar_weight: float
) -> Image.Image:
    """Mirror the app's premultiplied copy + lighter state blend."""
    weights = np.array(
        [
            (1.0 - blink_weight) * (1.0 - roar_weight),
            blink_weight * (1.0 - roar_weight),
            roar_weight,
        ],
        dtype=np.float32,
    )
    arrays = [np.asarray(states[state], dtype=np.float32) / 255.0 for state in STATES]
    alphas = [array[..., 3:4] for array in arrays]
    premultiplied = [array[..., :3] * array[..., 3:4] for array in arrays]
    alpha = sum(weights[index] * alphas[index] for index in range(3))
    rgbp = sum(weights[index] * premultiplied[index] for index in range(3))
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    out = np.concatenate((rgb, alpha), axis=2)
    return Image.fromarray(np.clip(np.rint(out * 255), 0, 255).astype(np.uint8))


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
        for y in (0, height - 1):
            if transparent[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((y, x))
    for y in range(height):
        for x in (0, width - 1):
            if transparent[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for dy, dx in (
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1), (0, 1),
            (1, -1), (1, 0), (1, 1),
        ):
            ny, nx = y + dy, x + dx
            if (
                0 <= ny < height
                and 0 <= nx < width
                and transparent[ny, nx]
                and not outside[ny, nx]
            ):
                outside[ny, nx] = True
                queue.append((ny, nx))
    holes = transparent & ~outside
    partial = (alpha > 0) & (alpha < 255)
    green_fringe = (
        partial
        & (array[..., 1].astype(np.int16) > array[..., 0].astype(np.int16) + 20)
        & (array[..., 1].astype(np.int16) > array[..., 2].astype(np.int16) + 20)
    )
    return {
        "dimensions": [image.width, image.height],
        "bbox_alpha_gt_8": bbox,
        "coverage_percent": round((bbox[2] - bbox[0]) / image.width * 100, 3),
        "padding_px_left_top_right_bottom": pads,
        "alpha_weighted_centroid": [round(value, 3) for value in centroid],
        "transparent_corner_alpha": [
            int(alpha[0, 0]),
            int(alpha[0, -1]),
            int(alpha[-1, 0]),
            int(alpha[-1, -1]),
        ],
        "partially_transparent_pixels": int(partial.sum()),
        "enclosed_fully_transparent_holes": int(holes.sum()),
        "green_dominant_partial_alpha_pixels": int(green_fringe.sum()),
    }


def main() -> None:
    for directory in (AUDIT, ALPHA, CHROMA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    masters = {state: rgba(ALPHA / f"{state}-{VERSION}.png") for state in STATES}
    if any(image.size != (1254, 1254) for image in masters.values()):
        raise RuntimeError("Party Parrot alpha masters must all be 1254 x 1254")

    master_alpha_hashes = {
        state: hashlib.sha256(image.getchannel("A").tobytes()).hexdigest()
        for state, image in masters.items()
    }
    if len(set(master_alpha_hashes.values())) != 1:
        raise RuntimeError("Party Parrot state alpha masks are not identity-locked")

    runtime_images: dict[str, Image.Image] = {}
    for state in STATES:
        candidate = AUDIT / f"candidate-{state}-{RUNTIME_SIDE}-q{RUNTIME_QUALITY}.webp"
        if not candidate.exists():
            raise RuntimeError(f"Missing reviewed runtime candidate: {candidate}")
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        shutil.copy2(candidate, public_path)
        shutil.copy2(candidate, PAGES / public_path.name)
        runtime_images[state] = rgba(public_path)

    native_images = [on_background(masters[state], checker((1254, 1254), 48)) for state in STATES]
    labeled_sheet(native_images, [f"{state} / native" for state in STATES], 3, 1254).save(
        AUDIT / f"native-states-{VERSION}.jpg", quality=92, optimize=True
    )

    runtime_380 = {
        state: image.resize((380, 380), Image.Resampling.LANCZOS)
        for state, image in runtime_images.items()
    }
    scale_images: list[Image.Image] = []
    scale_labels: list[str] = []
    for state in STATES:
        scale_images.append(on_background(runtime_380[state], "#eef2f6"))
        scale_labels.append(f"{state} / 380px")
    for state in STATES:
        tiny = runtime_images[state].resize((96, 96), Image.Resampling.LANCZOS)
        scale_images.append(on_background(tiny, "#eef2f6").resize((380, 380), Image.Resampling.NEAREST))
        scale_labels.append(f"{state} / 96px (4x)")
    labeled_sheet(scale_images, scale_labels, 3, 380).save(
        AUDIT / f"native-96-380-states-{VERSION}.png", optimize=True
    )

    hostile_images: list[Image.Image] = []
    hostile_labels: list[str] = []
    backgrounds: list[tuple[str, Image.Image | str]] = [
        ("white", "#ffffff"),
        ("black", "#000000"),
        ("cyan", "#00e8ff"),
        ("magenta", "#ff00dc"),
        ("green", "#00ff00"),
        ("checker", checker((380, 380))),
    ]
    for background_name, background in backgrounds:
        for state in STATES:
            hostile_images.append(on_background(runtime_380[state], background))
            hostile_labels.append(f"{state} / {background_name}")
    labeled_sheet(hostile_images, hostile_labels, 3, 380).save(
        AUDIT / f"hostile-380-states-{VERSION}.png", optimize=True
    )

    blend_images: list[Image.Image] = []
    blend_labels: list[str] = []
    for roar_weight in (0.0, 0.33, 0.67, 1.0):
        for blink_weight in (0.0, 0.33, 0.67, 1.0):
            mix = copy_lighter_mix(runtime_images, blink_weight, roar_weight)
            mix_380 = mix.resize((380, 380), Image.Resampling.LANCZOS)
            blend_images.append(on_background(mix_380, "#233048"))
            blend_labels.append(f"blink {blink_weight:.2f} / roar {roar_weight:.2f}")
    labeled_sheet(blend_images, blend_labels, 4, 380).save(
        AUDIT / f"copy-lighter-crossfades-380-{VERSION}.png", optimize=True
    )

    neutral_array = np.asarray(masters["neutral"].convert("RGB"), dtype=np.int16)
    neutral_alpha = np.asarray(masters["neutral"].getchannel("A"))
    visible = neutral_alpha > 0
    masks = {
        "blink": np.asarray(Image.open(AUDIT / f"blink-localization-mask-{VERSION}.png").convert("L")),
        "roar": np.asarray(Image.open(AUDIT / f"roar-localization-mask-{VERSION}.png").convert("L")),
    }
    stability: dict[str, dict[str, object]] = {}
    for state in ("blink", "roar"):
        state_array = np.asarray(masters[state].convert("RGB"), dtype=np.int16)
        channel_delta = np.max(np.abs(state_array - neutral_array), axis=2)
        changed = (channel_delta > 2) & visible
        cy, cx = np.where(changed)
        outside = masks[state] == 0
        stability[state] = {
            "changed_visible_pixels": int(changed.sum()),
            "changed_visible_percent": round(float(changed.sum() / visible.sum() * 100), 4),
            "changed_bbox": [int(cx.min()), int(cy.min()), int(cx.max()) + 1, int(cy.max()) + 1],
            "outside_localization_max_channel_delta": int(
                np.abs(state_array - neutral_array)[outside].max()
            ),
        }

    runtime_alpha_hashes = {
        state: hashlib.sha256(image.getchannel("A").tobytes()).hexdigest()
        for state, image in runtime_images.items()
    }
    candidate_sizes: dict[str, list[int]] = {}
    for side in (1254, 1344, 1408):
        for quality in (94, 95):
            paths = [AUDIT / f"candidate-{state}-{side}-q{quality}.webp" for state in STATES]
            if all(path.exists() for path in paths):
                candidate_sizes[f"{side}-q{quality}"] = [path.stat().st_size for path in paths]

    manifest: dict[str, object] = {
        "animal": "parrot",
        "name": "Party Parrot",
        "version": VERSION,
        "generation_route": "built-in ImageGen; Bumblebee v1 was finish/composition reference only; blink and roar used the generated neutral as sole edit target; expression changes were localized onto the neutral/shared alpha",
        "generated_sources": {
            "neutral": "design/runtime/parrot/chroma/neutral-v1.png",
            "blink": "design/runtime/parrot/audit/blink-generated-full-v1.png",
            "roar": "design/runtime/parrot/audit/roar-generated-full-v1.png",
        },
        "runtime_export": {
            "side_px": RUNTIME_SIDE,
            "quality": RUNTIME_QUALITY,
            "method": 6,
            "alpha_quality": 100,
        },
        "candidate_sizes_bytes": candidate_sizes,
        "master_alpha_pixel_hashes": master_alpha_hashes,
        "master_alpha_pixel_hashes_identical": len(set(master_alpha_hashes.values())) == 1,
        "runtime_alpha_pixel_hashes": runtime_alpha_hashes,
        "runtime_alpha_pixel_hashes_identical": len(set(runtime_alpha_hashes.values())) == 1,
        "state_stability": stability,
        "states": {},
        "audit_evidence": [
            f"design/runtime/parrot/audit/native-states-{VERSION}.jpg",
            f"design/runtime/parrot/audit/native-96-380-states-{VERSION}.png",
            f"design/runtime/parrot/audit/hostile-380-states-{VERSION}.png",
            f"design/runtime/parrot/audit/copy-lighter-crossfades-380-{VERSION}.png",
        ],
    }
    for state, image in masters.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        chroma_path = CHROMA / f"{state}-{VERSION}.png"
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        pages_path = PAGES / public_path.name
        manifest["states"][state] = {  # type: ignore[index]
            "chroma": str(chroma_path.relative_to(ROOT)),
            "chroma_sha256": sha256(chroma_path),
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "runtime": str(public_path.relative_to(ROOT)),
            "runtime_bytes": public_path.stat().st_size,
            "runtime_sha256": sha256(public_path),
            "github_pages_sha256": sha256(pages_path),
            "runtime_copies_identical": sha256(public_path) == sha256(pages_path),
            "contains_alph_chunk": b"ALPH" in public_path.read_bytes(),
            "metrics": alpha_metrics(image),
        }
    (AUDIT / f"manifest-{VERSION}.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
