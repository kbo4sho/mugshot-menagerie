#!/usr/bin/env python3
"""Localize, harmonize, export, and audit Rumble Rhino v1."""

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
RHINO = ROOT / "design/runtime/rhino"
AUDIT = RHINO / "audit"
CHROMA = RHINO / "chroma"
ALPHA = RHINO / "alpha"
PUBLIC = ROOT / "public/masks/rhino"
PAGES = ROOT / "github-pages/public/masks/rhino"
STATES = ("neutral", "blink", "roar-mid", "roar")
VERSION = "v1"
CANVAS = (1254, 1254)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def feathered_mask(
    size: tuple[int, int], boxes: tuple[tuple[int, int, int, int], ...], blur: float
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
        sheet.paste(image.convert("RGB"), (x, y + label_height))
        draw.text((x + 10, y + 10), labels[index], fill="#f4f4f7")
    return sheet


def copy_lighter_mix(
    states: dict[str, Image.Image], blink_weight: float, roar_weight: float
) -> Image.Image:
    """Mirror app/page.tsx weighted premultiplied copy + lighter blending."""
    if roar_weight <= 0.5:
        roar_mid = roar_weight * 2.0
        base = 1.0 - roar_mid
        weights = np.array(
            [(1.0 - blink_weight) * base, blink_weight * base, roar_mid, 0.0],
            dtype=np.float32,
        )
    else:
        roar = (roar_weight - 0.5) * 2.0
        weights = np.array([0.0, 0.0, 1.0 - roar, roar], dtype=np.float32)
    arrays = [np.asarray(states[state], dtype=np.float32) / 255.0 for state in STATES]
    alphas = [array[..., 3:4] for array in arrays]
    premultiplied = [array[..., :3] * array[..., 3:4] for array in arrays]
    alpha = sum(weights[index] * alphas[index] for index in range(4))
    rgbp = sum(weights[index] * premultiplied[index] for index in range(4))
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
        if transparent[0, x]:
            queue.append((0, x))
            outside[0, x] = True
        if transparent[height - 1, x] and not outside[height - 1, x]:
            queue.append((height - 1, x))
            outside[height - 1, x] = True
    for y in range(height):
        if transparent[y, 0] and not outside[y, 0]:
            queue.append((y, 0))
            outside[y, 0] = True
        if transparent[y, width - 1] and not outside[y, width - 1]:
            queue.append((y, width - 1))
            outside[y, width - 1] = True
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
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
    for directory in (AUDIT, CHROMA, ALPHA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    generated_paths = {state: AUDIT / f"generated-{state}-{VERSION}.png" for state in STATES}
    generated = {state: Image.open(path).convert("RGB") for state, path in generated_paths.items()}
    if any(image.size != CANVAS for image in generated.values()):
        raise RuntimeError("All generated rhino state masters must be 1254 x 1254")

    extracted_path = AUDIT / f"neutral-extracted-{VERSION}.png"
    helper = Path.home() / ".codex/skills/.system/imagegen/scripts/remove_chroma_key.py"
    subprocess.run(
        [
            sys.executable,
            str(helper),
            "--input",
            str(generated_paths["neutral"]),
            "--out",
            str(extracted_path),
            "--auto-key",
            "border",
            "--soft-matte",
            "--transparent-threshold",
            "12",
            "--opaque-threshold",
            "220",
            "--despill",
            "--edge-contract",
            "1",
            "--force",
        ],
        check=True,
    )
    neutral = rgba(extracted_path)
    neutral_alpha = neutral.getchannel("A")
    neutral_rgb = neutral.convert("RGB")

    # The targeted full-roar retry kept the correct single cavity but still
    # started it above the authored bridge. Compress that generated mouth patch
    # downward so the bridge and full roar share one top anchor and the cavity
    # grows toward the chin. All pixels still come from the neutral-targeted
    # full-roar generation; this is only a compact geometry registration.
    roar_source = neutral_rgb.copy()
    brow_only = feathered_mask(
        CANVAS, ((275, 325, 515, 530), (739, 325, 979, 530)), blur=18
    )
    roar_source = Image.composite(generated["roar"], roar_source, brow_only)
    smile_side_clear = feathered_mask(
        CANVAS, ((500, 995, 575, 1085), (680, 995, 755, 1085)), blur=10
    )
    roar_source = Image.composite(generated["roar"], roar_source, smile_side_clear)
    smile_side_clear.save(AUDIT / f"roar-smile-side-clear-mask-{VERSION}.png")
    roar_crop = generated["roar"].crop((550, 950, 705, 1130)).resize(
        (155, 145), Image.Resampling.LANCZOS
    )
    roar_patch = neutral_rgb.copy()
    roar_patch.paste(roar_crop, (550, 995))
    roar_patch_mask = feathered_mask(CANVAS, ((550, 995, 705, 1140),), blur=10)
    roar_source = Image.composite(roar_patch, roar_source, roar_patch_mask)
    roar_patch_mask.save(AUDIT / f"roar-mouth-geometry-repair-mask-{VERSION}.png")
    generated["roar"] = roar_source

    # Expression edits stay deep inside the neutral silhouette. Neutral owns
    # every perimeter pixel, the horn and ear crop, and the shared skin field.
    blink_mask = feathered_mask(
        CANVAS,
        ((250, 485, 540, 810), (714, 485, 1004, 810)),
        blur=20,
    )
    roar_mask = feathered_mask(
        CANVAS,
        ((485, 885, 769, 1170), (275, 325, 515, 530), (739, 325, 979, 530)),
        blur=18,
    )
    safe_interior = neutral_alpha.filter(ImageFilter.MinFilter(41))
    masks = {
        "blink": ImageChops.multiply(blink_mask, safe_interior),
        "roar-mid": ImageChops.multiply(roar_mask, safe_interior),
        "roar": ImageChops.multiply(roar_mask, safe_interior),
    }
    for state, mask in masks.items():
        mask.save(AUDIT / f"{state}-localization-mask-{VERSION}.png")

    masters: dict[str, Image.Image] = {"neutral": neutral}
    for state in ("blink", "roar-mid", "roar"):
        localized_rgb = Image.composite(generated[state], neutral_rgb, masks[state])
        localized = localized_rgb.convert("RGBA")
        localized.putalpha(neutral_alpha)
        masters[state] = localized

    for state, image in masters.items():
        image.putalpha(neutral_alpha)
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        chroma = Image.new("RGBA", CANVAS, "#00ff00")
        chroma.alpha_composite(image)
        chroma.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    # Prefer the largest q94-95 export where every state is in the requested
    # 200-350KB operational band.
    candidates: dict[tuple[int, int], list[int]] = {}
    chosen_side: int | None = None
    chosen_quality: int | None = None
    for side in (1254, 1152, 1024):
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
        for side in (1254, 1152, 1024):
            for quality in (95, 94):
                if max(candidates[(side, quality)]) <= 350_000:
                    chosen_side, chosen_quality = side, quality
                    break
            if chosen_side is not None:
                break
    if chosen_side is None or chosen_quality is None:
        raise RuntimeError("No q94-95 Rhino export stayed under 350KB")

    runtime_images: dict[str, Image.Image] = {}
    for state, image in masters.items():
        runtime = image if chosen_side == 1254 else image.resize((chosen_side, chosen_side), Image.Resampling.LANCZOS)
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        runtime.save(public_path, "WEBP", quality=chosen_quality, alpha_quality=100, method=6, exact=True)
        shutil.copy2(public_path, PAGES / public_path.name)
        runtime_images[state] = rgba(public_path)

    # Native, runtime, and thumbnail inspections.
    native_images = [on_background(masters[state], checker(CANVAS, 48)) for state in STATES]
    labeled_sheet(native_images, [f"{state} / native" for state in STATES], 4, CANVAS[0]).save(
        AUDIT / f"native-states-{VERSION}.jpg", quality=90, optimize=True
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
    labeled_sheet(scale_images, scale_labels, 4, 380).save(
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
    labeled_sheet(hostile_images, hostile_labels, 4, 380).save(
        AUDIT / f"hostile-380-states-{VERSION}.png", optimize=True
    )

    # Full runtime blend grid plus a closer roar-only semantic-mouth sequence.
    blend_images: list[Image.Image] = []
    blend_labels: list[str] = []
    blend_weights = (0.0, 0.33, 0.67, 1.0)
    for roar_weight in blend_weights:
        for blink_weight in blend_weights:
            mix = copy_lighter_mix(runtime_images, blink_weight, roar_weight)
            mix_380 = mix.resize((380, 380), Image.Resampling.LANCZOS)
            blend_images.append(on_background(mix_380, "#233048"))
            blend_labels.append(f"blink {blink_weight:.2f} / roar {roar_weight:.2f}")
    labeled_sheet(blend_images, blend_labels, 4, 380).save(
        AUDIT / f"copy-lighter-crossfades-380-{VERSION}.png", optimize=True
    )
    mouth_images: list[Image.Image] = []
    mouth_labels: list[str] = []
    for weight in (0.0, 0.33, 0.67, 1.0):
        mix = copy_lighter_mix(runtime_images, 0.0, weight).resize((380, 380), Image.Resampling.LANCZOS)
        crop = mix.crop((130, 245, 250, 365)).resize((380, 380), Image.Resampling.LANCZOS)
        mouth_images.append(on_background(crop, "#eef2f6"))
        mouth_labels.append(f"roar {weight:.2f} / mouth")
    labeled_sheet(mouth_images, mouth_labels, 4, 380).save(
        AUDIT / f"semantic-mouth-crossfade-{VERSION}.png", optimize=True
    )

    # Rhino-vs-hippo read check uses the shipped Hippo neutral solely as a
    # diagnostic comparison; the horn hierarchy should make Rhino immediate.
    hippo_path = ROOT / "public/masks/hippo/neutral-v1.webp"
    if hippo_path.exists():
        hippo = rgba(hippo_path).resize((380, 380), Image.Resampling.LANCZOS)
        labeled_sheet(
            [on_background(runtime_380["neutral"], "#eef2f6"), on_background(hippo, "#eef2f6")],
            ["Rumble Rhino v1", "Bubble Hippo v1"],
            2,
            380,
        ).save(AUDIT / f"species-vs-hippo-380-{VERSION}.png", optimize=True)

    # Canonical crop evidence: visible alpha bbox, center axes, and silhouette.
    placement = on_background(runtime_380["neutral"], checker((380, 380))).convert("RGB")
    placement_draw = ImageDraw.Draw(placement)
    alpha_380 = np.asarray(runtime_380["neutral"].getchannel("A"))
    py, px = np.where(alpha_380 > 8)
    placement_draw.rectangle(
        (int(px.min()), int(py.min()), int(px.max()), int(py.max())), outline="#ff3b6b", width=2
    )
    placement_draw.line((190, 0, 190, 379), fill="#5ce1e6", width=1)
    placement_draw.line((0, 190, 379, 190), fill="#5ce1e6", width=1)
    silhouette = Image.fromarray(np.dstack((np.zeros_like(alpha_380), np.zeros_like(alpha_380), np.zeros_like(alpha_380), alpha_380)).astype(np.uint8), "RGBA")
    labeled_sheet(
        [placement, on_background(silhouette, "#ffffff")],
        ["380px bbox + center", "shared alpha silhouette"],
        2,
        380,
    ).save(AUDIT / f"canonical-placement-380-{VERSION}.png", optimize=True)

    master_alpha_hashes = {
        state: hashlib.sha256(image.getchannel("A").tobytes()).hexdigest()
        for state, image in masters.items()
    }
    runtime_alpha_hashes = {
        state: hashlib.sha256(image.getchannel("A").tobytes()).hexdigest()
        for state, image in runtime_images.items()
    }
    neutral_array = np.asarray(masters["neutral"].convert("RGB"), dtype=np.int16)
    visible = np.asarray(neutral_alpha) > 0
    stability: dict[str, dict[str, object]] = {}
    for state in ("blink", "roar-mid", "roar"):
        state_array = np.asarray(masters[state].convert("RGB"), dtype=np.int16)
        channel_delta = np.max(np.abs(state_array - neutral_array), axis=2)
        changed = (channel_delta > 2) & visible
        cy, cx = np.where(changed)
        outside = np.asarray(masks[state]) == 0
        stability[state] = {
            "changed_visible_pixels": int(changed.sum()),
            "changed_visible_percent": round(float(changed.sum() / visible.sum() * 100), 4),
            "changed_bbox": [int(cx.min()), int(cy.min()), int(cx.max()) + 1, int(cy.max()) + 1],
            "outside_localization_max_channel_delta": int(
                np.abs(state_array - neutral_array)[outside].max()
            ),
        }

    manifest: dict[str, object] = {
        "animal": "rhino",
        "name": "Rumble Rhino",
        "version": VERSION,
        "generation_route": "built-in ImageGen; Bumblebee v1 was finish/composition reference only; blink, roar-mid, and roar used the generated Rhino neutral as sole edit target",
        "deterministic_processing": "installed chroma helper; localized expressions; shared neutral alpha; compact vertical registration of the neutral-targeted full-roar mouth; q95 WebP export",
        "generated_sources": {
            state: str(path.relative_to(ROOT)) for state, path in generated_paths.items()
        },
        "runtime_export": {
            "side_px": chosen_side,
            "quality": chosen_quality,
            "method": 6,
            "alpha_quality": 100,
        },
        "candidate_sizes_bytes": {
            f"{side}-q{quality}": values
            for (side, quality), values in candidates.items()
        },
        "master_alpha_pixel_hashes": master_alpha_hashes,
        "master_alpha_pixel_hashes_identical": len(set(master_alpha_hashes.values())) == 1,
        "runtime_alpha_pixel_hashes": runtime_alpha_hashes,
        "runtime_alpha_pixel_hashes_identical": len(set(runtime_alpha_hashes.values())) == 1,
        "state_stability": stability,
        "states": {},
        "audit_evidence": [
            f"design/runtime/rhino/audit/native-states-{VERSION}.jpg",
            f"design/runtime/rhino/audit/native-96-380-states-{VERSION}.png",
            f"design/runtime/rhino/audit/hostile-380-states-{VERSION}.png",
            f"design/runtime/rhino/audit/copy-lighter-crossfades-380-{VERSION}.png",
            f"design/runtime/rhino/audit/semantic-mouth-crossfade-{VERSION}.png",
            f"design/runtime/rhino/audit/species-vs-hippo-380-{VERSION}.png",
            f"design/runtime/rhino/audit/canonical-placement-380-{VERSION}.png",
            f"design/runtime/rhino/audit/prompts-and-provenance-{VERSION}.md",
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
