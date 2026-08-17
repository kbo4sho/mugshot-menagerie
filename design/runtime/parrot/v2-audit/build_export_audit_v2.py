#!/usr/bin/env python3
"""Audit the critic-directed Party Parrot v2 beak-transition repair."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[4]
PARROT = ROOT / "design/runtime/parrot"
AUDIT = PARROT / "v2-audit"
PUBLIC = ROOT / "public/masks/parrot"
PAGES = ROOT / "github-pages/public/masks/parrot"
STATES = ("neutral", "blink", "roar")
WEIGHTS = (0.10, 0.33, 0.50, 0.67, 0.75)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def on_background(image: Image.Image, color: str) -> Image.Image:
    base = Image.new("RGBA", image.size, color)
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


def domain_mask(points: list[tuple[int, int]]) -> np.ndarray:
    image = Image.new("L", (1254, 1254), 0)
    ImageDraw.Draw(image).polygon(points, fill=255)
    return np.asarray(image) > 0


def main() -> None:
    masters_v1 = {state: rgba(PARROT / f"alpha/{state}-v1.png") for state in STATES}
    masters_v2 = {state: rgba(PARROT / f"alpha/{state}-v2.png") for state in STATES}
    runtime_v1 = {state: rgba(PUBLIC / f"{state}-v1.webp") for state in STATES}
    runtime_v2 = {state: rgba(PUBLIC / f"{state}-v2.webp") for state in STATES}

    # Required visual probes from shipped WebPs.
    for side in (96, 380):
        images: list[Image.Image] = []
        labels: list[str] = []
        for weight in WEIGHTS:
            frame = mix(runtime_v2["neutral"], runtime_v2["roar"], weight)
            frame = frame.resize((side, side), Image.Resampling.LANCZOS)
            framed = on_background(frame, "#233048")
            if side == 96:
                framed = framed.resize((380, 380), Image.Resampling.NEAREST)
            images.append(framed)
            labels.append(f"v2 roar {weight:.2f} / {side}px")
        labeled_sheet(images, labels, 5, 380).save(
            AUDIT / f"roar-transition-{side}-v2.png", optimize=True
        )

    comparison_images: list[Image.Image] = []
    comparison_labels: list[str] = []
    for version, states in (("v1", runtime_v1), ("v2", runtime_v2)):
        for weight in (0.33, 0.67, 1.0):
            frame = mix(states["neutral"], states["roar"], weight).resize(
                (380, 380), Image.Resampling.LANCZOS
            )
            comparison_images.append(on_background(frame, "#233048"))
            comparison_labels.append(f"{version} roar {weight:.2f}")
    labeled_sheet(comparison_images, comparison_labels, 3, 380).save(
        AUDIT / "v1-v2-roar-comparison-380.png", optimize=True
    )

    static_images: list[Image.Image] = []
    static_labels: list[str] = []
    for side in (380, 96):
        for state in STATES:
            frame = runtime_v2[state].resize((side, side), Image.Resampling.LANCZOS)
            framed = on_background(frame, "#eef2f6")
            if side == 96:
                framed = framed.resize((380, 380), Image.Resampling.NEAREST)
            static_images.append(framed)
            static_labels.append(f"{state} / {side}px")
    labeled_sheet(static_images, static_labels, 3, 380).save(
        AUDIT / "native-96-380-states-v2.png", optimize=True
    )

    # Multi-threshold change topology in the single intended aperture domain.
    cavity_domain = domain_mask(
        [(520, 790), (734, 790), (744, 850), (720, 915),
         (675, 960), (579, 960), (534, 915), (510, 850)]
    )
    pale_wrap_image = Image.new("L", (1254, 1254), 0)
    pale_wrap_draw = ImageDraw.Draw(pale_wrap_image)
    pale_wrap_draw.polygon(
        [(500, 815), (548, 815), (560, 870), (590, 925),
         (580, 950), (540, 925), (510, 875)],
        fill=255,
    )
    pale_wrap_draw.polygon(
        [(754, 815), (706, 815), (694, 870), (664, 925),
         (674, 950), (714, 925), (744, 875)],
        fill=255,
    )
    pale_wrap_domain = np.asarray(pale_wrap_image) > 0
    neutral_array = np.asarray(masters_v2["neutral"], dtype=np.float32)
    roar_array = np.asarray(masters_v2["roar"], dtype=np.float32)
    topology: dict[str, object] = {}
    for weight in WEIGHTS:
        frame = neutral_array * (1.0 - weight) + roar_array * weight
        delta = np.max(np.abs(frame[..., :3] - neutral_array[..., :3]), axis=2)
        thresholds: dict[str, object] = {}
        for threshold in (2, 8, 16, 32):
            active = (delta >= threshold) & cavity_domain
            sizes = component_sizes(active)
            total = sum(sizes)
            thresholds[str(threshold)] = {
                "active_pixels": int(active.sum()),
                "components_ge_4px": len(sizes),
                "largest_component_pixels": sizes[0] if sizes else 0,
                "largest_component_share": round(sizes[0] / total, 4) if total else None,
            }
        red, green, blue = frame[..., 0], frame[..., 1], frame[..., 2]
        pale = (
            pale_wrap_domain
            & (red > 150)
            & (green > 100)
            & (blue > 65)
            & ((red - blue) < 160)
        )
        topology[f"{weight:.2f}"] = {
            "thresholds": thresholds,
            "pale_side_wrap_pixels": int(pale.sum()),
            "pale_side_wrap_domain_pixels": int(pale_wrap_domain.sum()),
            "pale_side_wrap_share": round(float(pale.sum() / pale_wrap_domain.sum()), 5),
        }

    localization = np.asarray(
        Image.open(AUDIT / "roar-final-localization-mask-v2.png").convert("L")
    )
    v1_roar = np.asarray(masters_v1["roar"], dtype=np.int16)
    v2_roar = np.asarray(masters_v2["roar"], dtype=np.int16)
    roar_delta = np.max(np.abs(v2_roar[..., :3] - v1_roar[..., :3]), axis=2)

    master_alpha_hashes = {
        state: hashlib.sha256(masters_v2[state].getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }
    runtime_alpha_hashes = {
        state: hashlib.sha256(runtime_v2[state].getchannel("A").tobytes()).hexdigest()
        for state in STATES
    }

    manifest: dict[str, object] = {
        "animal": "parrot",
        "name": "Party Parrot",
        "version": "v2",
        "repair": "critic-directed deterministic mouth/beak ROI repair; v1 preserved; the one permitted ImageGen target was audited but rejected because its dark U still wrapped the cavity",
        "runtime_export": {
            "side_px": 1344,
            "quality": 95,
            "method": 6,
            "alpha_quality": 100,
        },
        "v1_preservation": {
            "neutral_master_pixels_identical_v1_v2": bool(
                np.array_equal(np.asarray(masters_v1["neutral"]), np.asarray(masters_v2["neutral"]))
            ),
            "blink_master_pixels_identical_v1_v2": bool(
                np.array_equal(np.asarray(masters_v1["blink"]), np.asarray(masters_v2["blink"]))
            ),
            "neutral_runtime_bytes_identical_v1_v2": (
                (PUBLIC / "neutral-v1.webp").read_bytes() == (PUBLIC / "neutral-v2.webp").read_bytes()
            ),
            "blink_runtime_bytes_identical_v1_v2": (
                (PUBLIC / "blink-v1.webp").read_bytes() == (PUBLIC / "blink-v2.webp").read_bytes()
            ),
        },
        "master_alpha_pixel_hashes": master_alpha_hashes,
        "master_alpha_pixel_hashes_identical": len(set(master_alpha_hashes.values())) == 1,
        "runtime_alpha_pixel_hashes": runtime_alpha_hashes,
        "runtime_alpha_pixel_hashes_identical": len(set(runtime_alpha_hashes.values())) == 1,
        "roar_repair_localization": {
            "changed_bbox": [int(value) for value in (
                np.where(roar_delta > 0)[1].min(),
                np.where(roar_delta > 0)[0].min(),
                np.where(roar_delta > 0)[1].max() + 1,
                np.where(roar_delta > 0)[0].max() + 1,
            )],
            "changed_pixels": int((roar_delta > 0).sum()),
            "localization_mask_nonzero_pixels": int((localization > 0).sum()),
            "outside_roi_max_channel_delta": int(roar_delta[localization == 0].max()),
            "outside_roi_changed_pixels": int(((roar_delta > 0) & (localization == 0)).sum()),
        },
        "multi_threshold_topology": topology,
        "states": {},
        "audit_evidence": [
            "design/runtime/parrot/v2-audit/roar-transition-96-v2.png",
            "design/runtime/parrot/v2-audit/roar-transition-380-v2.png",
            "design/runtime/parrot/v2-audit/v1-v2-roar-comparison-380.png",
            "design/runtime/parrot/v2-audit/native-96-380-states-v2.png",
        ],
    }
    for state in STATES:
        alpha_path = PARROT / f"alpha/{state}-v2.png"
        chroma_path = PARROT / f"chroma/{state}-v2.png"
        public_path = PUBLIC / f"{state}-v2.webp"
        pages_path = PAGES / f"{state}-v2.webp"
        manifest["states"][state] = {  # type: ignore[index]
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
        }
    (AUDIT / "manifest-v2.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
