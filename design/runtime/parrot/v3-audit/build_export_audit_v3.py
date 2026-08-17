#!/usr/bin/env python3
"""Build and audit the critic-directed Party Parrot v3 lower-beak repair."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
PARROT = ROOT / "design/runtime/parrot"
AUDIT = PARROT / "v3-audit"
ALPHA = PARROT / "alpha"
CHROMA = PARROT / "chroma"
PUBLIC = ROOT / "public/masks/parrot"
PAGES = ROOT / "github-pages/public/masks/parrot"
STATES = ("neutral", "blink", "roar")
WEIGHTS = (0.10, 0.33, 0.50, 0.67, 0.75)
MASTER_SIDE = 1254
RUNTIME_SIDE = 1344


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def checker(size: tuple[int, int], cell: int = 24) -> Image.Image:
    out = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(out)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            fill = "#d8d8d8" if (x // cell + y // cell) % 2 else "#f7f7f7"
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=fill)
    return out


def on_background(image: Image.Image, background: Image.Image | str) -> Image.Image:
    base = (
        Image.new("RGBA", image.size, background)
        if isinstance(background, str)
        else background.convert("RGBA")
    )
    base.alpha_composite(image.convert("RGBA"))
    return base.convert("RGB")


def labeled_sheet(images: list[Image.Image], labels: list[str], columns: int, cell: int) -> Image.Image:
    rows = (len(images) + columns - 1) // columns
    label_height = 34
    out = Image.new("RGB", (columns * cell, rows * (cell + label_height)), "#1c1c22")
    draw = ImageDraw.Draw(out)
    for index, image in enumerate(images):
        x = index % columns * cell
        y = index // columns * (cell + label_height)
        out.paste(image.convert("RGB"), (x, y + label_height))
        draw.text((x + 8, y + 9), labels[index], fill="white")
    return out


def mix(neutral: Image.Image, roar: Image.Image, weight: float) -> Image.Image:
    na = np.asarray(neutral, dtype=np.float32)
    ra = np.asarray(roar, dtype=np.float32)
    out = np.rint(na * (1.0 - weight) + ra * weight).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out)


def component_sizes(mask: np.ndarray, minimum_size: int = 4) -> list[int]:
    seen = np.zeros_like(mask, dtype=bool)
    sizes: list[int] = []
    height, width = mask.shape
    for y, x in zip(*np.where(mask)):
        if seen[y, x]:
            continue
        queue: deque[tuple[int, int]] = deque([(int(y), int(x))])
        seen[y, x] = True
        size = 0
        while queue:
            yy, xx = queue.popleft()
            size += 1
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = yy + dy, xx + dx
                    if (
                        0 <= ny < height
                        and 0 <= nx < width
                        and mask[ny, nx]
                        and not seen[ny, nx]
                    ):
                        seen[ny, nx] = True
                        queue.append((ny, nx))
        if size >= minimum_size:
            sizes.append(size)
    return sorted(sizes, reverse=True)


def alpha_metrics(image: Image.Image) -> dict[str, object]:
    array = np.asarray(image.convert("RGBA"))
    alpha = array[..., 3]
    ys, xs = np.where(alpha > 8)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
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
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
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
        "padding_px_left_top_right_bottom": [
            bbox[0], bbox[1], image.width - bbox[2], image.height - bbox[3]
        ],
        "alpha_weighted_centroid": [round(value, 3) for value in centroid],
        "transparent_corner_alpha": [
            int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])
        ],
        "partially_transparent_pixels": int(partial.sum()),
        "enclosed_fully_transparent_holes": int(holes.sum()),
        "green_dominant_partial_alpha_pixels": int(green_fringe.sum()),
    }


def build_roar_v3() -> tuple[Image.Image, Image.Image, Image.Image]:
    """Replace the detached crescent and broaden the attached lower mandible."""
    base = rgba(ALPHA / "roar-v2.png")
    array = np.asarray(base, dtype=np.float32)
    height, width = array.shape[:2]

    # Replace the detached dark crescent with scarlet texture sampled laterally
    # from the same lower-feather rows. Cross-blending symmetric samples avoids
    # a clone seam while retaining real feather grain and lighting.
    sampled = array.copy()
    for y in range(950, 1025):
        for x in range(540, 715):
            t = max(0.0, min(1.0, (x - 570) / 117))
            xl = max(0, x - 90)
            xr = min(width - 1, x + 90)
            sampled[y, x, :3] = (1.0 - t) * array[y, xl, :3] + t * array[y, xr, :3]
    sampled_image = Image.fromarray(np.clip(np.rint(sampled), 0, 255).astype(np.uint8))

    crescent_mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(crescent_mask).polygon(
        [
            (570, 976), (590, 969), (609, 972), (627, 979), (647, 972),
            (671, 969), (687, 978), (682, 995), (662, 1007), (639, 1013),
            (615, 1012), (590, 1006), (575, 995),
        ],
        fill=255,
    )
    crescent_mask = crescent_mask.filter(ImageFilter.GaussianBlur(5))
    repaired = Image.composite(sampled_image, base, crescent_mask)

    # Reuse the existing horn material, stretched only laterally, so the lower
    # mandible becomes a single broader rounded piece still joined to the cavity.
    horn_source = repaired.crop((594, 929, 662, 970))
    horn_stretched = horn_source.resize((80, 41), Image.Resampling.LANCZOS)
    horn_mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(horn_mask).polygon(
        [
            (610, 930), (646, 930), (661, 939), (666, 950), (659, 962),
            (643, 970), (613, 970), (597, 963), (590, 950), (595, 939),
        ],
        fill=255,
    )
    horn_mask = horn_mask.filter(ImageFilter.GaussianBlur(1.6))
    horn_layer = repaired.copy()
    horn_layer.alpha_composite(horn_stretched, (588, 929))
    output = Image.composite(horn_layer, repaired, horn_mask)
    output.putalpha(base.getchannel("A"))
    return output, crescent_mask, horn_mask


def main() -> None:
    for directory in (AUDIT, ALPHA, CHROMA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    # Preserve v2 and state identity. Neutral/blink are exact copies; roar starts
    # from v2 and changes only the final mouth-bottom repair region.
    for state in ("neutral", "blink"):
        shutil.copy2(ALPHA / f"{state}-v2.png", ALPHA / f"{state}-v3.png")
        shutil.copy2(CHROMA / f"{state}-v2.png", CHROMA / f"{state}-v3.png")
        shutil.copy2(PUBLIC / f"{state}-v2.webp", PUBLIC / f"{state}-v3.webp")
        shutil.copy2(PUBLIC / f"{state}-v2.webp", PAGES / f"{state}-v3.webp")

    roar, crescent_mask, horn_mask = build_roar_v3()
    roar.save(ALPHA / "roar-v3.png", optimize=True)
    crescent_mask.save(AUDIT / "roar-detached-crescent-replacement-mask-v3.png", optimize=True)
    horn_mask.save(AUDIT / "roar-lower-mandible-reshape-mask-v3.png", optimize=True)
    final_mask = ImageChops.lighter(crescent_mask, horn_mask)
    final_mask.save(AUDIT / "roar-final-localization-mask-v3.png", optimize=True)

    green = Image.new("RGB", roar.size, "#00ff00")
    green.paste(roar.convert("RGB"), mask=roar.getchannel("A"))
    green.save(CHROMA / "roar-v3.png", optimize=True)

    resized = roar.resize((RUNTIME_SIDE, RUNTIME_SIDE), Image.Resampling.LANCZOS)
    candidate_png = AUDIT / "candidate-roar-1344-v3.png"
    candidate_webp = AUDIT / "candidate-roar-1344-q95-v3.webp"
    resized.save(candidate_png, optimize=True)
    subprocess.run(
        [
            "/opt/homebrew/bin/cwebp", "-quiet", "-q", "95", "-alpha_q", "100",
            "-m", "6", "-exact", str(candidate_png), "-o", str(candidate_webp),
        ],
        check=True,
    )
    shutil.copy2(candidate_webp, PUBLIC / "roar-v3.webp")
    shutil.copy2(candidate_webp, PAGES / "roar-v3.webp")

    masters_v1 = {state: rgba(ALPHA / f"{state}-v1.png") for state in STATES}
    masters_v2 = {state: rgba(ALPHA / f"{state}-v2.png") for state in STATES}
    masters_v3 = {state: rgba(ALPHA / f"{state}-v3.png") for state in STATES}
    runtime_v2 = {state: rgba(PUBLIC / f"{state}-v2.webp") for state in STATES}
    runtime_v3 = {state: rgba(PUBLIC / f"{state}-v3.webp") for state in STATES}

    # Native/static and hostile-background visual evidence.
    static_images: list[Image.Image] = []
    static_labels: list[str] = []
    for side in (380, 96):
        for state in STATES:
            frame = runtime_v3[state].resize((side, side), Image.Resampling.LANCZOS)
            framed = on_background(frame, "#eef2f6")
            if side == 96:
                framed = framed.resize((380, 380), Image.Resampling.NEAREST)
            static_images.append(framed)
            static_labels.append(f"{state} / {side}px")
    labeled_sheet(static_images, static_labels, 3, 380).save(
        AUDIT / "native-96-380-states-v3.png", optimize=True
    )

    native = [on_background(masters_v3[state], checker((MASTER_SIDE, MASTER_SIDE), 48)) for state in STATES]
    labeled_sheet(native, [f"{state} / native" for state in STATES], 3, MASTER_SIDE).save(
        AUDIT / "native-states-v3.jpg", quality=92, optimize=True
    )

    hostile_images: list[Image.Image] = []
    hostile_labels: list[str] = []
    for name, color in (("white", "#ffffff"), ("black", "#000000"), ("cyan", "#00e8ff"),
                        ("magenta", "#ff00dc"), ("green", "#00ff00")):
        for state in STATES:
            frame = runtime_v3[state].resize((380, 380), Image.Resampling.LANCZOS)
            hostile_images.append(on_background(frame, color))
            hostile_labels.append(f"{state} / {name}")
    labeled_sheet(hostile_images, hostile_labels, 3, 380).save(
        AUDIT / "hostile-380-states-v3.png", optimize=True
    )

    for side in (96, 380):
        images: list[Image.Image] = []
        labels: list[str] = []
        for weight in WEIGHTS:
            frame = mix(runtime_v3["neutral"], runtime_v3["roar"], weight)
            frame = frame.resize((side, side), Image.Resampling.LANCZOS)
            framed = on_background(frame, "#233048")
            if side == 96:
                framed = framed.resize((380, 380), Image.Resampling.NEAREST)
            images.append(framed)
            labels.append(f"v3 roar {weight:.2f} / {side}px")
        labeled_sheet(images, labels, 5, 380).save(
            AUDIT / f"roar-transition-{side}-v3.png", optimize=True
        )

    compare_images: list[Image.Image] = []
    compare_labels: list[str] = []
    for version, states in (("v2", runtime_v2), ("v3", runtime_v3)):
        for weight in (0.33, 0.67, 1.0):
            frame = mix(states["neutral"], states["roar"], weight).resize(
                (380, 380), Image.Resampling.LANCZOS
            )
            compare_images.append(on_background(frame, "#233048"))
            compare_labels.append(f"{version} roar {weight:.2f}")
    labeled_sheet(compare_images, compare_labels, 3, 380).save(
        AUDIT / "v2-v3-roar-comparison-380.png", optimize=True
    )

    # Quantify only the local v2 -> v3 repair and transition topology.
    v2_roar = np.asarray(masters_v2["roar"], dtype=np.int16)
    v3_roar = np.asarray(masters_v3["roar"], dtype=np.int16)
    delta = np.max(np.abs(v3_roar[..., :3] - v2_roar[..., :3]), axis=2)
    localization = np.asarray(final_mask) > 0
    ys, xs = np.where(delta > 0)

    mouth_domain_image = Image.new("L", (MASTER_SIDE, MASTER_SIDE), 0)
    ImageDraw.Draw(mouth_domain_image).polygon(
        [(500, 790), (754, 790), (748, 865), (714, 925), (673, 974),
         (627, 1000), (581, 974), (540, 925), (506, 865)], fill=255
    )
    mouth_domain = np.asarray(mouth_domain_image) > 0
    neutral_array = np.asarray(masters_v3["neutral"], dtype=np.float32)
    roar_array = np.asarray(masters_v3["roar"], dtype=np.float32)
    topology: dict[str, object] = {}
    for weight in WEIGHTS:
        frame = neutral_array * (1.0 - weight) + roar_array * weight
        changed = np.max(np.abs(frame[..., :3] - neutral_array[..., :3]), axis=2)
        thresholds: dict[str, object] = {}
        for threshold in (2, 8, 16, 32):
            active = (changed >= threshold) & mouth_domain
            sizes = component_sizes(active)
            total = sum(sizes)
            thresholds[str(threshold)] = {
                "active_pixels": int(active.sum()),
                "components_ge_4px": len(sizes),
                "largest_component_pixels": sizes[0] if sizes else 0,
                "largest_component_share": round(sizes[0] / total, 4) if total else None,
            }
        topology[f"{weight:.2f}"] = {"thresholds": thresholds}

    master_alpha_hashes = {
        state: hashlib.sha256(masters_v3[state].getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }
    runtime_alpha_hashes = {
        state: hashlib.sha256(runtime_v3[state].getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }

    crescent_core = np.zeros((MASTER_SIDE, MASTER_SIDE), dtype=bool)
    crescent_core[978:1008, 575:685] = True
    horn_core = np.zeros((MASTER_SIDE, MASTER_SIDE), dtype=bool)
    horn_core[930:970, 590:666] = True

    def dark_mask(image: np.ndarray) -> np.ndarray:
        rgb = image[..., :3]
        return (rgb[..., 0] < 130) & (rgb[..., 1] < 65) & (rgb[..., 2] < 65)

    def charcoal_mask(image: np.ndarray) -> np.ndarray:
        rgb = image[..., :3].astype(np.int16)
        return ((rgb.max(axis=2) - rgb.min(axis=2)) < 60) & (rgb.mean(axis=2) < 80)

    def dark_bbox(image: np.ndarray, domain: np.ndarray) -> list[int]:
        ys_dark, xs_dark = np.where(charcoal_mask(image) & domain)
        return [
            int(xs_dark.min()), int(ys_dark.min()),
            int(xs_dark.max()) + 1, int(ys_dark.max()) + 1,
        ]

    v2_horn_bbox = dark_bbox(v2_roar, horn_core)
    v3_horn_bbox = dark_bbox(v3_roar, horn_core)

    manifest: dict[str, object] = {
        "animal": "parrot",
        "name": "Party Parrot",
        "version": "v3",
        "repair": (
            "critic-directed deterministic v2 mouth-bottom repair: detached dark crescent "
            "replaced with sampled scarlet feather texture; existing compact lower horn "
            "widened laterally while kept attached to the continuous v2 burgundy cavity"
        ),
        "imagegen_used": False,
        "runtime_export": {"side_px": 1344, "quality": 95, "method": 6, "alpha_quality": 100},
        "preservation": {
            "v1_v2_files_still_present": all(
                (ALPHA / f"{state}-{version}.png").exists()
                and (PUBLIC / f"{state}-{version}.webp").exists()
                for state in STATES for version in ("v1", "v2")
            ),
            "neutral_master_pixels_identical_v1_v2_v3": bool(
                np.array_equal(np.asarray(masters_v1["neutral"]), np.asarray(masters_v2["neutral"]))
                and np.array_equal(np.asarray(masters_v2["neutral"]), np.asarray(masters_v3["neutral"]))
            ),
            "blink_master_pixels_identical_v1_v2_v3": bool(
                np.array_equal(np.asarray(masters_v1["blink"]), np.asarray(masters_v2["blink"]))
                and np.array_equal(np.asarray(masters_v2["blink"]), np.asarray(masters_v3["blink"]))
            ),
            "neutral_runtime_bytes_identical_v2_v3": (
                (PUBLIC / "neutral-v2.webp").read_bytes() == (PUBLIC / "neutral-v3.webp").read_bytes()
            ),
            "blink_runtime_bytes_identical_v2_v3": (
                (PUBLIC / "blink-v2.webp").read_bytes() == (PUBLIC / "blink-v3.webp").read_bytes()
            ),
        },
        "master_alpha_pixel_hashes": master_alpha_hashes,
        "master_alpha_pixel_hashes_identical": len(set(master_alpha_hashes.values())) == 1,
        "runtime_alpha_pixel_hashes": runtime_alpha_hashes,
        "runtime_alpha_pixel_hashes_identical": len(set(runtime_alpha_hashes.values())) == 1,
        "roar_v2_to_v3_localization": {
            "changed_bbox": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
            "changed_pixels": int((delta > 0).sum()),
            "localization_mask_nonzero_pixels": int(localization.sum()),
            "outside_roi_max_channel_delta": int(delta[~localization].max()),
            "outside_roi_changed_pixels": int(((delta > 0) & ~localization).sum()),
            "changed_pixels_above_y929": int(((delta > 0) & (np.indices(delta.shape)[0] < 929)).sum()),
        },
        "critic_artifact_metrics": {
            "detached_crescent_core_xyxy": [575, 978, 685, 1008],
            "detached_crescent_dark_pixels_v2": int((dark_mask(v2_roar) & crescent_core).sum()),
            "detached_crescent_dark_pixels_v3": int((dark_mask(v3_roar) & crescent_core).sum()),
            "detached_crescent_charcoal_pixels_v2": int((charcoal_mask(v2_roar) & crescent_core).sum()),
            "detached_crescent_charcoal_pixels_v3": int((charcoal_mask(v3_roar) & crescent_core).sum()),
            "attached_lower_horn_dark_bbox_v2": v2_horn_bbox,
            "attached_lower_horn_dark_bbox_v3": v3_horn_bbox,
            "attached_lower_horn_dark_width_v2": v2_horn_bbox[2] - v2_horn_bbox[0],
            "attached_lower_horn_dark_width_v3": v3_horn_bbox[2] - v3_horn_bbox[0],
        },
        "multi_threshold_topology": topology,
        "states": {},
        "audit_evidence": [
            "design/runtime/parrot/v3-audit/repair-record-v3.md",
            "design/runtime/parrot/v3-audit/native-states-v3.jpg",
            "design/runtime/parrot/v3-audit/native-96-380-states-v3.png",
            "design/runtime/parrot/v3-audit/hostile-380-states-v3.png",
            "design/runtime/parrot/v3-audit/roar-transition-96-v3.png",
            "design/runtime/parrot/v3-audit/roar-transition-380-v3.png",
            "design/runtime/parrot/v3-audit/v2-v3-roar-comparison-380.png",
        ],
    }
    for state in STATES:
        alpha_path = ALPHA / f"{state}-v3.png"
        chroma_path = CHROMA / f"{state}-v3.png"
        public_path = PUBLIC / f"{state}-v3.webp"
        pages_path = PAGES / f"{state}-v3.webp"
        state_entry = {
            "alpha_master": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "chroma": str(chroma_path.relative_to(ROOT)),
            "chroma_sha256": sha256(chroma_path),
            "runtime": str(public_path.relative_to(ROOT)),
            "runtime_bytes": public_path.stat().st_size,
            "runtime_sha256": sha256(public_path),
            "github_pages_sha256": sha256(pages_path),
            "runtime_copies_identical": public_path.read_bytes() == pages_path.read_bytes(),
            "contains_alph_chunk": b"ALPH" in public_path.read_bytes(),
            "alpha_metrics_master": alpha_metrics(masters_v3[state]),
            "alpha_metrics_runtime": alpha_metrics(runtime_v3[state]),
        }
        manifest["states"][state] = state_entry  # type: ignore[index]

    (AUDIT / "manifest-v3.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
