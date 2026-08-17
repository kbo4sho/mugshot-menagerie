from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[4]
PIG = ROOT / "design" / "runtime" / "pig"
ALPHA = PIG / "alpha"
CHROMA = PIG / "chroma"
AUDIT = PIG / "audit"
PUBLIC = ROOT / "public" / "masks" / "pig"
PAGES = ROOT / "github-pages" / "public" / "masks" / "pig"
STATES = ("neutral", "blink", "roar")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checker(size: tuple[int, int], cell: int = 24) -> Image.Image:
    width, height = size
    out = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(out)
    for y in range(0, height, cell):
        for x in range(0, width, cell):
            color = "#d8d8d8" if (x // cell + y // cell) % 2 else "#f7f7f7"
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=color)
    return out


def on_background(foreground: Image.Image, background: Image.Image | str) -> Image.Image:
    base = Image.new("RGBA", foreground.size, background) if isinstance(background, str) else background.convert("RGBA")
    return Image.alpha_composite(base, foreground).convert("RGB")


def weighted_runtime_blend(images: dict[str, Image.Image], blink_weight: float, roar_weight: float) -> Image.Image:
    # Mirrors app/page.tsx: neutral=(1-blink)*(1-roar),
    # blink=blink*(1-roar), roar=roar, composited with copy + lighter.
    weights = {
        "neutral": (1.0 - blink_weight) * (1.0 - roar_weight),
        "blink": blink_weight * (1.0 - roar_weight),
        "roar": roar_weight,
    }
    arrays = {state: np.asarray(image.convert("RGBA"), dtype=np.float32) / 255.0 for state, image in images.items()}
    out_alpha = np.zeros((*images["neutral"].size[::-1], 1), dtype=np.float32)
    out_rgb_p = np.zeros((*images["neutral"].size[::-1], 3), dtype=np.float32)
    for state, weight in weights.items():
        pixels = arrays[state]
        alpha = pixels[..., 3:4]
        out_alpha += alpha * weight
        out_rgb_p += pixels[..., :3] * alpha * weight
    out_rgb = np.divide(out_rgb_p, out_alpha, out=np.zeros_like(out_rgb_p), where=out_alpha > 1e-8)
    out = np.concatenate((out_rgb, out_alpha), axis=2)
    return Image.fromarray(np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8))


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    PAGES.mkdir(parents=True, exist_ok=True)

    images = {state: Image.open(ALPHA / f"{state}-v1.png").convert("RGBA") for state in STATES}
    locked_alpha = images["neutral"].getchannel("A")
    for state, image in images.items():
        image.putalpha(locked_alpha)
        image.save(ALPHA / f"{state}-v1.png", optimize=True)
        chroma = Image.new("RGBA", image.size, "#00ff00")
        chroma.alpha_composite(image)
        chroma.convert("RGB").save(CHROMA / f"{state}-v1.png", optimize=True)
        images[state] = image

    exports: dict[str, dict[str, object]] = {}
    for state, image in images.items():
        target = PUBLIC / f"{state}-v1.webp"
        image.save(target, "WEBP", quality=94, alpha_quality=100, method=6, exact=True)
        pages_target = PAGES / target.name
        pages_target.write_bytes(target.read_bytes())
        decoded = Image.open(target).convert("RGBA")
        decoded_alpha_hash = hashlib.sha256(decoded.getchannel("A").tobytes()).hexdigest()
        exports[state] = {
            "public_path": str(target.relative_to(ROOT)),
            "pages_path": str(pages_target.relative_to(ROOT)),
            "bytes": target.stat().st_size,
            "sha256": sha256(target),
            "pages_sha256": sha256(pages_target),
            "pages_byte_equal": target.read_bytes() == pages_target.read_bytes(),
            "has_alph_chunk": b"ALPH" in target.read_bytes(),
            "decoded_alpha_sha256": decoded_alpha_hash,
            "decoded_alpha_matches_master": decoded_alpha_hash == hashlib.sha256(locked_alpha.tobytes()).hexdigest(),
        }

    # Everything below reviews the actual decoded runtime WebPs, not only the
    # lossless masters, so compression behavior is part of the evidence.
    images = {state: Image.open(PUBLIC / f"{state}-v1.webp").convert("RGBA") for state in STATES}

    native = Image.new("RGB", (1254 * 3, 1254), "#ececf1")
    for index, state in enumerate(STATES):
        native.paste(on_background(images[state], checker(images[state].size, 48)), (index * 1254, 0))
    native.save(AUDIT / "native-states-v1.jpg", quality=91, optimize=True)

    thumbs = Image.new("RGB", (96 * 3, 96), "#ececf1")
    for index, state in enumerate(STATES):
        thumb = images[state].resize((96, 96), Image.Resampling.LANCZOS)
        thumbs.paste(on_background(thumb, checker((96, 96), 12)), (index * 96, 0))
    thumbs.save(AUDIT / "states-96-v1.png", optimize=True)

    small = {state: image.resize((380, 380), Image.Resampling.LANCZOS) for state, image in images.items()}
    backgrounds: list[Image.Image | str] = [
        "#ffffff",
        "#101018",
        "#00ff00",
        "#ff00ff",
        "#00ffff",
        checker((380, 380)),
    ]
    hostile = Image.new("RGB", (380 * 3, 380 * len(backgrounds)), "#777777")
    for row, background in enumerate(backgrounds):
        for col, state in enumerate(STATES):
            hostile.paste(on_background(small[state], background), (col * 380, row * 380))
    hostile.save(AUDIT / "hostile-380-states-v1.png", optimize=True)

    weights = (0.0, 0.25, 0.5, 0.75, 1.0)
    crossfade = Image.new("RGB", (380 * len(weights), 380 * 3), "#17171f")
    rows = (
        [(weight, 0.0) for weight in weights],
        [(0.0, weight) for weight in weights],
        [(0.75, weight) for weight in weights],
    )
    for row, pairs in enumerate(rows):
        for col, (blink_weight, roar_weight) in enumerate(pairs):
            blend = weighted_runtime_blend(images, blink_weight, roar_weight).resize((380, 380), Image.Resampling.LANCZOS)
            crossfade.paste(on_background(blend, checker((380, 380))), (col * 380, row * 380))
    crossfade.save(AUDIT / "copy-lighter-crossfades-380-v1.png", optimize=True)

    alpha_array = np.asarray(locked_alpha)
    ys, xs = np.where(alpha_array > 0)
    binary_alpha = Image.fromarray(np.where(alpha_array > 0, 255, 0).astype(np.uint8)).copy()
    ImageDraw.floodfill(binary_alpha, (0, 0), 128)
    enclosed_hole_pixels = int((np.asarray(binary_alpha) == 0).sum())
    neutral_rgb = np.asarray(images["neutral"], dtype=np.int16)[..., :3]
    state_stability: dict[str, dict[str, object]] = {}
    for state, image in images.items():
        pixels = np.asarray(image)
        partial = (pixels[..., 3] > 0) & (pixels[..., 3] < 255)
        green_dominant = (
            (pixels[..., 1].astype(np.int16) > pixels[..., 0].astype(np.int16) + 30)
            & (pixels[..., 1].astype(np.int16) > pixels[..., 2].astype(np.int16) + 30)
            & partial
        )
        record: dict[str, object] = {"green_dominant_partial_alpha_pixels": int(green_dominant.sum())}
        if state != "neutral":
            delta = np.max(np.abs(pixels[..., :3].astype(np.int16) - neutral_rgb), axis=2)
            changed = (delta > 2) & (alpha_array > 0)
            changed_y, changed_x = np.where(changed)
            record.update(
                {
                    "changed_visible_pixels": int(changed.sum()),
                    "changed_visible_percent": float(changed.sum() / (alpha_array > 0).sum() * 100),
                    "changed_bbox": [int(changed_x.min()), int(changed_y.min()), int(changed_x.max() + 1), int(changed_y.max() + 1)],
                }
            )
        state_stability[state] = record

    metrics = {
        "version": "v1",
        "native_dimensions": list(images["neutral"].size),
        "runtime_dimensions": list(images["neutral"].size),
        "review_dimensions": [380, 380],
        "alpha_bbox": [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)],
        "alpha_centroid": [float(xs.mean()), float(ys.mean())],
        "padding_px": {
            "left": int(xs.min()),
            "top": int(ys.min()),
            "right": int(images["neutral"].width - 1 - xs.max()),
            "bottom": int(images["neutral"].height - 1 - ys.max()),
        },
        "nonzero_alpha_pixels": int((alpha_array > 0).sum()),
        "partial_alpha_pixels": int(((alpha_array > 0) & (alpha_array < 255)).sum()),
        "corner_alpha": [int(alpha_array[0, 0]), int(alpha_array[0, -1]), int(alpha_array[-1, 0]), int(alpha_array[-1, -1])],
        "enclosed_hole_pixels": enclosed_hole_pixels,
        "alpha_sha256": hashlib.sha256(locked_alpha.tobytes()).hexdigest(),
        "state_stability": state_stability,
        "exports": exports,
    }
    (AUDIT / "manifest-v1.json").write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
