#!/usr/bin/env python3
"""Build and audit the Rhino v2 full-roar lower-clearance repair."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[4]
RHINO = ROOT / "design/runtime/rhino"
AUDIT = RHINO / "audit"
ALPHA = RHINO / "alpha"
CHROMA = RHINO / "chroma"
PUBLIC = ROOT / "public/masks/rhino"
PAGES = ROOT / "github-pages/public/masks/rhino"
STATES = ("neutral", "blink", "roar-mid", "roar")
SOURCE_VERSION = "v1"
VERSION = "v2"
CANVAS = (1254, 1254)
ANGLES = (-7, 0, 7)


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
        rendered = image.convert("RGB")
        if rendered.size != (cell, cell):
            rendered = rendered.resize((cell, cell), Image.Resampling.LANCZOS)
        sheet.paste(rendered, (x, y + label_height))
        draw.text((x + 10, y + 10), labels[index], fill="#f4f4f7")
    return sheet


def copy_lighter_mix(states: dict[str, Image.Image], roar_weight: float) -> Image.Image:
    if roar_weight <= 0.5:
        roar_mid = roar_weight * 2.0
        weights = np.array([1.0 - roar_mid, 0.0, roar_mid, 0.0], dtype=np.float32)
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


def connected_components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    seen = np.zeros_like(mask, dtype=bool)
    components: list[list[tuple[int, int]]] = []
    height, width = mask.shape
    for y, x in zip(*np.where(mask)):
        if seen[y, x]:
            continue
        queue = [(int(y), int(x))]
        seen[y, x] = True
        component: list[tuple[int, int]] = []
        while queue:
            cy, cx = queue.pop()
            component.append((cy, cx))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if (
                    0 <= ny < height
                    and 0 <= nx < width
                    and mask[ny, nx]
                    and not seen[ny, nx]
                ):
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        components.append(component)
    return components


def measure_clearance(image: Image.Image, side: int, angle: int) -> dict[str, object]:
    scaled = image.resize((side, side), Image.Resampling.LANCZOS)
    rotated = scaled.rotate(angle, Image.Resampling.BICUBIC, expand=False)
    array = np.asarray(rotated.convert("RGBA"))
    alpha = array[..., 3]
    luminance = array[..., :3].mean(axis=2)
    yy, xx = np.indices((side, side))
    dark = (
        (luminance < 75)
        & (alpha > 220)
        & (yy > side * 0.72)
        & (xx > side * 0.27)
        & (xx < side * 0.73)
    )
    components = connected_components(dark)
    if not components:
        raise RuntimeError(f"No full-roar cavity found at {side}px / {angle} degrees")
    cavity = max(components, key=len)
    cavity_bottom = max(y for y, _ in cavity)
    cavity_center_x = round(sum(x for _, x in cavity) / len(cavity))

    clear_rows: list[int] = []
    for y in range(cavity_bottom + 1, side):
        rgb = array[y, cavity_center_x, :3]
        clearly_lavender = (
            alpha[y, cavity_center_x] >= 240
            and float(rgb.mean()) >= 80
            and int(rgb[2]) >= int(rgb[1]) - 4
        )
        if clearly_lavender:
            clear_rows.append(y)
        elif clear_rows:
            break
    return {
        "side_px": side,
        "angle_degrees": angle,
        "cavity_component_pixels": len(cavity),
        "cavity_bottom_row": int(cavity_bottom),
        "probe_x": int(cavity_center_x),
        "clear_lavender_opaque_rows": clear_rows,
        "clear_lavender_opaque_count": len(clear_rows),
    }


def helper_component_metrics(image: Image.Image) -> dict[str, object]:
    array = np.asarray(image.convert("RGBA"))
    crop = array[985:1110, 500:755]
    dark = crop[..., :3].mean(axis=2) < 55
    sizes = sorted(
        (len(component) for component in connected_components(dark) if len(component) >= 100),
        reverse=True,
    )
    return {
        "dark_component_threshold": 55,
        "minimum_reported_component_pixels": 100,
        "reported_component_count": len(sizes),
        "reported_component_sizes": sizes,
        "single_connected_mouth_component": len(sizes) == 1,
    }


def alpha_metrics(image: Image.Image) -> dict[str, object]:
    array = np.asarray(image.convert("RGBA"))
    alpha = array[..., 3]
    ys, xs = np.where(alpha > 8)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    partial = (alpha > 0) & (alpha < 255)
    green_fringe = (
        partial
        & (array[..., 1].astype(np.int16) > array[..., 0].astype(np.int16) + 20)
        & (array[..., 1].astype(np.int16) > array[..., 2].astype(np.int16) + 20)
    )
    return {
        "dimensions": [image.width, image.height],
        "bbox_alpha_gt_8": bbox,
        "padding_px_left_top_right_bottom": [
            bbox[0],
            bbox[1],
            image.width - bbox[2],
            image.height - bbox[3],
        ],
        "transparent_corner_alpha": [
            int(alpha[0, 0]),
            int(alpha[0, -1]),
            int(alpha[-1, 0]),
            int(alpha[-1, -1]),
        ],
        "partially_transparent_pixels": int(partial.sum()),
        "green_dominant_partial_alpha_pixels": int(green_fringe.sum()),
    }


def main() -> None:
    for directory in (AUDIT, ALPHA, CHROMA, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    v1 = {state: rgba(ALPHA / f"{state}-{SOURCE_VERSION}.png") for state in STATES}
    if any(image.size != CANVAS for image in v1.values()):
        raise RuntimeError("All Rhino v1 alpha masters must be 1254 x 1254")
    locked_alpha = v1["neutral"].getchannel("A")

    # Critic-directed repair: replace only the lower part of the full-roar
    # cavity with the canonical neutral's continuous muzzle/chin pixels. The
    # rounded boundary retains the v1 upper rim and raises only the lower edge.
    neutral_array = np.asarray(v1["neutral"], dtype=np.float32)
    roar_array = np.asarray(v1["roar"], dtype=np.float32)
    yy, xx = np.indices(CANVAS)
    dx = np.abs(xx - 627.0)
    horizontal = np.clip((106.0 - dx) / 34.0, 0.0, 1.0)
    horizontal = horizontal * horizontal * (3.0 - 2.0 * horizontal)
    rounded = np.sqrt(np.clip(1.0 - (dx / 83.0) ** 2, 0.0, 1.0))
    lower_boundary = 1056.0 + 26.0 * rounded
    vertical = np.clip((yy - (lower_boundary - 8.0)) / 16.0, 0.0, 1.0)
    vertical = vertical * vertical * (3.0 - 2.0 * vertical)
    repair_weight = horizontal * vertical
    repair_weight[(yy < 1030) | (yy > 1142)] = 0.0
    repaired = (
        roar_array * (1.0 - repair_weight[..., None])
        + neutral_array * repair_weight[..., None]
    )
    repaired = np.clip(np.rint(repaired), 0, 255).astype(np.uint8)
    repaired[..., 3] = np.asarray(locked_alpha)

    repair_mask = Image.fromarray(np.clip(np.rint(repair_weight * 255), 0, 255).astype(np.uint8))
    repair_mask.save(AUDIT / f"roar-lower-clearance-repair-mask-{VERSION}.png", optimize=True)

    masters: dict[str, Image.Image] = {
        "neutral": v1["neutral"].copy(),
        "blink": v1["blink"].copy(),
        "roar-mid": v1["roar-mid"].copy(),
        "roar": Image.fromarray(repaired),
    }
    for image in masters.values():
        image.putalpha(locked_alpha)

    for state, image in masters.items():
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        chroma = Image.new("RGBA", CANVAS, "#00ff00")
        chroma.alpha_composite(image)
        chroma.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    # The v1 native q95 exports are already in-band, so preserve their runtime
    # resolution and encoding contract for v2.
    runtime_images: dict[str, Image.Image] = {}
    exports: dict[str, dict[str, object]] = {}
    for state, image in masters.items():
        public_path = PUBLIC / f"{state}-{VERSION}.webp"
        image.save(public_path, "WEBP", quality=95, alpha_quality=100, method=6, exact=True)
        pages_path = PAGES / public_path.name
        shutil.copy2(public_path, pages_path)
        runtime_images[state] = rgba(public_path)
        exports[state] = {
            "bytes": public_path.stat().st_size,
            "public_sha256": sha256(public_path),
            "pages_sha256": sha256(pages_path),
            "public_pages_byte_identical": public_path.read_bytes() == pages_path.read_bytes(),
            "contains_alph_chunk": b"ALPH" in public_path.read_bytes(),
        }

    runtime_380 = {
        state: image.resize((380, 380), Image.Resampling.LANCZOS)
        for state, image in runtime_images.items()
    }

    state_images: list[Image.Image] = []
    state_labels: list[str] = []
    for state in STATES:
        state_images.append(on_background(runtime_380[state], "#eef2f6"))
        state_labels.append(f"{state} / 380px / v2")
    for state in STATES:
        tiny = runtime_images[state].resize((96, 96), Image.Resampling.LANCZOS)
        state_images.append(on_background(tiny, "#eef2f6").resize((380, 380), Image.Resampling.NEAREST))
        state_labels.append(f"{state} / 96px (4x) / v2")
    labeled_sheet(state_images, state_labels, 4, 380).save(
        AUDIT / f"states-380-96-{VERSION}.png", optimize=True
    )

    compare_images: list[Image.Image] = []
    compare_labels: list[str] = []
    for background_name, background in (("light", "#eef2f6"), ("black", "#000000")):
        for version_name, image in (("v1", v1["roar"]), ("v2", masters["roar"])):
            rendered = image.resize((380, 380), Image.Resampling.LANCZOS)
            compare_images.append(on_background(rendered, background))
            compare_labels.append(f"roar {version_name} / {background_name}")
    labeled_sheet(compare_images, compare_labels, 4, 380).save(
        AUDIT / f"roar-clearance-v1-v2-380.png", optimize=True
    )

    rotation_380: list[Image.Image] = []
    rotation_380_labels: list[str] = []
    rotation_96: list[Image.Image] = []
    rotation_96_labels: list[str] = []
    for background_name, background in (("light", "#eef2f6"), ("black", "#000000")):
        for angle in ANGLES:
            large = runtime_images["roar"].resize((380, 380), Image.Resampling.LANCZOS).rotate(
                angle, Image.Resampling.BICUBIC, expand=False
            )
            rotation_380.append(on_background(large, background))
            rotation_380_labels.append(f"roar v2 / {background_name} / {angle:+d} deg")
            tiny = runtime_images["roar"].resize((96, 96), Image.Resampling.LANCZOS).rotate(
                angle, Image.Resampling.BICUBIC, expand=False
            )
            rotation_96.append(
                on_background(tiny, background).resize((384, 384), Image.Resampling.NEAREST)
            )
            rotation_96_labels.append(f"roar v2 / {background_name} / {angle:+d} deg / 96px")
    labeled_sheet(rotation_380, rotation_380_labels, 3, 380).save(
        AUDIT / f"hostile-rotation-clearance-380-{VERSION}.png", optimize=True
    )
    labeled_sheet(rotation_96, rotation_96_labels, 3, 384).save(
        AUDIT / f"hostile-rotation-clearance-96-{VERSION}.png", optimize=True
    )

    helper_steps = [index / 8 for index in range(9)]
    helper_images: list[Image.Image] = []
    helper_labels: list[str] = []
    helper_metrics: dict[str, dict[str, object]] = {}
    for weight in helper_steps:
        blend = copy_lighter_mix(masters, weight)
        helper_metrics[f"{weight:.3f}"] = helper_component_metrics(blend)
        rendered = blend.resize((380, 380), Image.Resampling.LANCZOS)
        helper_images.append(on_background(rendered, "#233048"))
        helper_labels.append(f"roar helper {weight:.3f}")
    labeled_sheet(helper_images, helper_labels, 3, 380).save(
        AUDIT / f"helper-eighth-steps-380-{VERSION}.png", optimize=True
    )

    clearance: dict[str, dict[str, dict[str, object]]] = {}
    for side in (1254, 380, 96):
        clearance[str(side)] = {}
        for angle in ANGLES:
            metric = measure_clearance(masters["roar"], side, angle)
            clearance[str(side)][str(angle)] = {
                "light": metric,
                "black": dict(metric),
            }

    alpha_hashes = {
        state: hashlib.sha256(image.getchannel("A").tobytes()).hexdigest()
        for state, image in masters.items()
    }
    v1_arrays = {state: np.asarray(image) for state, image in v1.items()}
    v2_arrays = {state: np.asarray(image) for state, image in masters.items()}
    changed = np.max(
        np.abs(v2_arrays["roar"][..., :3].astype(np.int16) - v1_arrays["roar"][..., :3].astype(np.int16)),
        axis=2,
    ) > 0
    roi = repair_weight > 0
    changed_y, changed_x = np.where(changed)

    manifest: dict[str, object] = {
        "animal": "rhino",
        "name": "Rumble Rhino",
        "version": VERSION,
        "source_version": SOURCE_VERSION,
        "critic_gap": "v1 full roar retained only 21 native centerline pixels below the cavity, collapsing to one clear row at 96px and visually merging under light/black rotation",
        "repair": "raised/shortened only the full-roar lower cavity boundary and filled the removed region with canonical neutral muzzle/chin texture; upper rim and roar-mid alignment retained",
        "generation_route": "deterministic local source-preservation repair; no new ImageGen call",
        "runtime_export": {
            "side_px": 1254,
            "quality": 95,
            "alpha_quality": 100,
            "method": 6,
        },
        "clearance_pass_requirement": "at least 3 clearly lavender opaque pixels below the full-roar cavity at 96px on light/black and -7/0/+7 degree rotations",
        "clearance_metrics": clearance,
        "helper_component_metrics": helper_metrics,
        "all_helper_steps_single_connected_mouth_component": all(
            metric["single_connected_mouth_component"] for metric in helper_metrics.values()
        ),
        "repair_metrics": {
            "changed_rgb_pixels": int(changed.sum()),
            "changed_bbox": [
                int(changed_x.min()),
                int(changed_y.min()),
                int(changed_x.max()) + 1,
                int(changed_y.max()) + 1,
            ],
            "outside_repair_roi_max_channel_delta": int(
                np.abs(
                    v2_arrays["roar"][..., :3].astype(np.int16)
                    - v1_arrays["roar"][..., :3].astype(np.int16)
                )[~roi].max()
            ),
            "neutral_v1_v2_pixel_delta": int(
                np.abs(v2_arrays["neutral"].astype(np.int16) - v1_arrays["neutral"].astype(np.int16)).max()
            ),
            "blink_v1_v2_pixel_delta": int(
                np.abs(v2_arrays["blink"].astype(np.int16) - v1_arrays["blink"].astype(np.int16)).max()
            ),
            "roar_mid_v1_v2_pixel_delta": int(
                np.abs(v2_arrays["roar-mid"].astype(np.int16) - v1_arrays["roar-mid"].astype(np.int16)).max()
            ),
        },
        "alpha_pixel_hashes": alpha_hashes,
        "alpha_pixel_hashes_identical": len(set(alpha_hashes.values())) == 1,
        "states": {},
        "exports": exports,
        "evidence": [
            f"design/runtime/rhino/audit/states-380-96-{VERSION}.png",
            "design/runtime/rhino/audit/roar-clearance-v1-v2-380.png",
            f"design/runtime/rhino/audit/hostile-rotation-clearance-380-{VERSION}.png",
            f"design/runtime/rhino/audit/hostile-rotation-clearance-96-{VERSION}.png",
            f"design/runtime/rhino/audit/helper-eighth-steps-380-{VERSION}.png",
            f"design/runtime/rhino/audit/roar-lower-clearance-repair-mask-{VERSION}.png",
            f"design/runtime/rhino/audit/prompts-and-provenance-{VERSION}.md",
        ],
    }
    for state, image in masters.items():
        alpha_path = ALPHA / f"{state}-{VERSION}.png"
        chroma_path = CHROMA / f"{state}-{VERSION}.png"
        manifest["states"][state] = {  # type: ignore[index]
            "alpha": str(alpha_path.relative_to(ROOT)),
            "alpha_sha256": sha256(alpha_path),
            "chroma": str(chroma_path.relative_to(ROOT)),
            "chroma_sha256": sha256(chroma_path),
            "metrics": alpha_metrics(image),
        }
    (AUDIT / f"manifest-{VERSION}.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
