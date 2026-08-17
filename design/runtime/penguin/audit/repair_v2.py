#!/usr/bin/env python3
"""Deterministically repair Party Penguin's v1 roar cavity as v2."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parents[4]
PENGUIN = ROOT / "design/runtime/penguin"
ALPHA = PENGUIN / "alpha"
CHROMA = PENGUIN / "chroma"
AUDIT = PENGUIN / "audit"
PUBLIC = ROOT / "public/masks/penguin"
PAGES = ROOT / "github-pages/public/masks/penguin"
STATES = ("neutral", "blink", "roar")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def supersampled_ellipse_mask(
    size: tuple[int, int], box: tuple[int, int, int, int], scale: int = 4
) -> Image.Image:
    large = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(large)
    draw.ellipse(tuple(value * scale for value in box), fill=255)
    return large.resize(size, Image.Resampling.LANCZOS)


def continuous_cavity_gradient(
    size: tuple[int, int],
    box: tuple[int, int, int, int],
    center_rgb: tuple[int, int, int],
    edge_rgb: tuple[int, int, int],
) -> Image.Image:
    """One radially continuous cavity surface, with no horizontal tonal split."""
    left, top, right, bottom = box
    cx = (left + right) / 2.0
    cy = (top + bottom) / 2.0
    rx = (right - left) / 2.0
    ry = (bottom - top) / 2.0
    yy, xx = np.mgrid[0:size[1], 0:size[0]]
    radius = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    # The fourth-power falloff keeps the main cavity an uninterrupted coral
    # field while adding only a narrow, continuous inner-edge shadow.
    amount = np.clip(radius, 0.0, 1.0) ** 4
    center = np.array(center_rgb, dtype=np.float32)
    edge = np.array(edge_rgb, dtype=np.float32)
    rgb = center[None, None, :] * (1.0 - amount[..., None]) + edge[None, None, :] * amount[..., None]
    alpha = np.full((*size[::-1], 1), 255, dtype=np.float32)
    return Image.fromarray(np.clip(np.rint(np.concatenate([rgb, alpha], axis=2)), 0, 255).astype(np.uint8))


def checker(size: tuple[int, int], cell: int = 24) -> Image.Image:
    out = Image.new("RGBA", size, (247, 247, 247, 255))
    draw = ImageDraw.Draw(out)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(210, 210, 216, 255))
    return out


def fit_square(image: Image.Image, side: int, margin: int = 10) -> Image.Image:
    thumb = image.copy()
    thumb.thumbnail((side - 2 * margin, side - 2 * margin), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(thumb, ((side - thumb.width) // 2, (side - thumb.height) // 2))
    return canvas


def composite_over(image: Image.Image, background: Image.Image | tuple[int, int, int], side: int) -> Image.Image:
    fitted = fit_square(image, side)
    if isinstance(background, tuple):
        bg = Image.new("RGBA", (side, side), (*background, 255))
    else:
        bg = background.convert("RGBA")
        if bg.size != (side, side):
            bg = bg.resize((side, side), Image.Resampling.BILINEAR)
    bg.alpha_composite(fitted)
    return bg.convert("RGB")


def labeled_sheet(images: list[Image.Image], labels: list[str], columns: int, cell: int) -> Image.Image:
    header = 34
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell, rows * (cell + header)), (28, 28, 34))
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(images):
        x = (index % columns) * cell
        y = (index // columns) * (cell + header)
        sheet.paste(image.convert("RGB"), (x, y + header))
        draw.text((x + 10, y + 9), labels[index], fill=(244, 244, 247))
    return sheet


def copy_lighter_mix(states: dict[str, Image.Image], blink: float, roar: float) -> Image.Image:
    weights = np.array([(1 - blink) * (1 - roar), blink * (1 - roar), roar], dtype=np.float32)
    arrays = [np.asarray(states[state].convert("RGBA"), dtype=np.float32) / 255.0 for state in STATES]
    premul = [array[..., :3] * array[..., 3:4] for array in arrays]
    alpha = sum(weights[index] * arrays[index][..., 3:4] for index in range(3))
    rgbp = sum(weights[index] * premul[index] for index in range(3))
    rgb = np.divide(rgbp, np.maximum(alpha, 1e-8), out=np.zeros_like(rgbp), where=alpha > 1e-8)
    out = np.concatenate([rgb, alpha], axis=2)
    return Image.fromarray(np.clip(np.rint(out * 255), 0, 255).astype(np.uint8))


def main() -> None:
    for directory in (ALPHA, CHROMA, AUDIT, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    # Neutral and blink remain byte-identical at master/runtime level.
    for state in ("neutral", "blink"):
        shutil.copy2(ALPHA / f"{state}-v1.png", ALPHA / f"{state}-v2.png")
        shutil.copy2(CHROMA / f"{state}-v1.png", CHROMA / f"{state}-v2.png")
        shutil.copy2(PUBLIC / f"{state}-v1.webp", PUBLIC / f"{state}-v2.webp")
        shutil.copy2(PUBLIC / f"{state}-v2.webp", PAGES / f"{state}-v2.webp")

    v1_roar = Image.open(ALPHA / "roar-v1.png").convert("RGBA")
    cavity_box = (569, 777, 685, 870)
    cavity_center_rgb = (232, 77, 66)
    cavity_edge_rgb = (159, 28, 24)
    cavity_mask = supersampled_ellipse_mask(v1_roar.size, cavity_box)
    cavity_mask = ImageChops.multiply(cavity_mask, v1_roar.getchannel("A"))
    cavity_mask.save(AUDIT / "roar-cavity-repair-mask-v2.png")

    coral_cavity = continuous_cavity_gradient(
        v1_roar.size, cavity_box, cavity_center_rgb, cavity_edge_rgb
    )
    repaired_roar = Image.composite(coral_cavity, v1_roar, cavity_mask)
    repaired_roar.putalpha(v1_roar.getchannel("A"))
    repaired_roar.save(ALPHA / "roar-v2.png", optimize=True)

    green = Image.new("RGBA", repaired_roar.size, (0, 255, 0, 255))
    green.alpha_composite(repaired_roar)
    green.convert("RGB").save(CHROMA / "roar-v2.png", optimize=True)

    repaired_roar.save(
        PUBLIC / "roar-v2.webp",
        "WEBP",
        quality=95,
        alpha_quality=100,
        method=6,
        exact=True,
    )
    shutil.copy2(PUBLIC / "roar-v2.webp", PAGES / "roar-v2.webp")

    states = {state: Image.open(ALPHA / f"{state}-v2.png").convert("RGBA") for state in STATES}
    runtime = {state: Image.open(PUBLIC / f"{state}-v2.webp").convert("RGBA") for state in STATES}

    native = [composite_over(states[state], checker(states[state].size, 48), 1254) for state in STATES]
    labeled_sheet(native, [f"{state} / native 1254px" for state in STATES], 3, 1254).save(
        AUDIT / "native-states-v2.jpg", quality=92, optimize=True
    )

    sized: list[Image.Image] = []
    sized_labels: list[str] = []
    for state in STATES:
        sized.append(composite_over(runtime[state], checker((380, 380)), 380))
        sized_labels.append(f"{state} / 380px")
    for state in STATES:
        sized.append(composite_over(runtime[state], (232, 237, 244), 96).resize((380, 380), Image.Resampling.NEAREST))
        sized_labels.append(f"{state} / 96px (4x)")
    labeled_sheet(sized, sized_labels, 3, 380).save(AUDIT / "native-and-96-states-v2.png")

    hostile: list[Image.Image] = []
    hostile_labels: list[str] = []
    for name, background in (
        ("white", (255, 255, 255)),
        ("near-black", (5, 6, 10)),
        ("navy", (16, 26, 62)),
        ("cyan", (0, 220, 255)),
        ("magenta", (255, 0, 220)),
    ):
        for state in STATES:
            hostile.append(composite_over(runtime[state], background, 380))
            hostile_labels.append(f"{state} / {name}")
    labeled_sheet(hostile, hostile_labels, 3, 380).save(AUDIT / "hostile-380-states-v2.png")

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
        mixes.append(composite_over(copy_lighter_mix(runtime, blink, roar), (17, 22, 36), 380))
        mix_labels.append(label)
    labeled_sheet(mixes, mix_labels, 5, 380).save(AUDIT / "copy-lighter-crossfades-380-v2.png")

    # Direct proof that only the selected interior cavity changed from v1.
    v1_arr = np.asarray(v1_roar, dtype=np.int16)
    v2_arr = np.asarray(repaired_roar, dtype=np.int16)
    delta = np.max(np.abs(v2_arr - v1_arr), axis=2)
    ys, xs = np.where(delta > 0)
    delta_bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    outside = np.asarray(cavity_mask) == 0

    alpha_hashes = {
        state: hashlib.sha256(states[state].getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }
    manifest = {
        "animal": "penguin",
        "name": "Party Penguin",
        "version": "v2",
        "method": "deterministic localized mouth-cavity repair; no ImageGen retry",
        "source_version": "v1",
        "neutral_and_blink_master_bytes_identical_to_v1": {
            state: (ALPHA / f"{state}-v1.png").read_bytes() == (ALPHA / f"{state}-v2.png").read_bytes()
            for state in ("neutral", "blink")
        },
        "neutral_and_blink_runtime_bytes_identical_to_v1": {
            state: (PUBLIC / f"{state}-v1.webp").read_bytes() == (PUBLIC / f"{state}-v2.webp").read_bytes()
            for state in ("neutral", "blink")
        },
        "repair": {
            "cavity_box_xyxy": list(cavity_box),
            "cavity_center_rgb": list(cavity_center_rgb),
            "cavity_edge_rgb": list(cavity_edge_rgb),
            "shading": "continuous radial fourth-power edge falloff; no horizontal tonal split",
            "antialias_supersampling": 4,
            "changed_pixel_bbox_xyxy": delta_bbox,
            "changed_pixels": int((delta > 0).sum()),
            "outside_repair_mask_max_channel_delta": int(np.abs(v2_arr - v1_arr)[outside].max()),
        },
        "runtime_export": {"side_px": 1254, "quality": 95, "alpha_quality": 100, "method": 6},
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "states": {},
    }
    for state in STATES:
        alpha_path = ALPHA / f"{state}-v2.png"
        runtime_path = PUBLIC / f"{state}-v2.webp"
        pages_path = PAGES / f"{state}-v2.webp"
        image = states[state]
        alpha = np.asarray(image.getchannel("A"))
        ys, xs = np.where(alpha > 8)
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        weights = alpha.astype(np.float64)
        total = weights.sum()
        centroid = [
            round(float((weights * np.arange(alpha.shape[1])[None, :]).sum() / total), 3),
            round(float((weights * np.arange(alpha.shape[0])[:, None]).sum() / total), 3),
        ]
        manifest["states"][state] = {
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "runtime": str(runtime_path.relative_to(ROOT)),
            "runtime_bytes": runtime_path.stat().st_size,
            "runtime_sha256": sha256(runtime_path),
            "github_pages_sha256": sha256(pages_path),
            "runtime_copies_identical": runtime_path.read_bytes() == pages_path.read_bytes(),
            "has_alph_chunk": b"ALPH" in runtime_path.read_bytes(),
            "bbox_alpha_gt_8": bbox,
            "padding_px_left_top_right_bottom": [bbox[0], bbox[1], image.width - bbox[2], image.height - bbox[3]],
            "alpha_weighted_centroid": centroid,
            "transparent_corner_alpha": [int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])],
        }
    (AUDIT / "manifest-v2.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
