from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[4]
HIPPO = ROOT / "design" / "runtime" / "hippo"
ALPHA = HIPPO / "alpha"
CHROMA = HIPPO / "chroma"
AUDIT = HIPPO / "audit"
PUBLIC = ROOT / "public" / "masks" / "hippo"
PAGES = ROOT / "github-pages" / "public" / "masks" / "hippo"
STATES = ("neutral", "blink", "roar")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checker(size: tuple[int, int], cell: int = 24) -> Image.Image:
    w, h = size
    out = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(out)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            color = "#d8d8d8" if (x // cell + y // cell) % 2 else "#f7f7f7"
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=color)
    return out


def on_background(foreground: Image.Image, background: Image.Image | str) -> Image.Image:
    if isinstance(background, str):
        base = Image.new("RGBA", foreground.size, background)
    else:
        base = background.convert("RGBA")
    return Image.alpha_composite(base, foreground).convert("RGB")


def weighted_blend(a: Image.Image, b: Image.Image, weight: float) -> Image.Image:
    # Premultiplied-alpha weighted sum mirrors the runtime's copy + lighter
    # behavior for one active expression channel.
    aa = np.asarray(a.convert("RGBA"), dtype=np.float32) / 255.0
    bb = np.asarray(b.convert("RGBA"), dtype=np.float32) / 255.0
    a_alpha = aa[..., 3:4]
    b_alpha = bb[..., 3:4]
    out_alpha = a_alpha * (1.0 - weight) + b_alpha * weight
    out_rgb_p = aa[..., :3] * a_alpha * (1.0 - weight) + bb[..., :3] * b_alpha * weight
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
            "decoded_alpha_matches_master": decoded_alpha_hash
            == hashlib.sha256(locked_alpha.tobytes()).hexdigest(),
        }

    # 380 px is the actual mask draw size. This sheet checks all states on the
    # most revealing hostile backgrounds, not just on a friendly neutral tile.
    small = {state: image.resize((380, 380), Image.Resampling.LANCZOS) for state, image in images.items()}
    backgrounds: list[tuple[str, Image.Image | str]] = [
        ("light", "#ffffff"),
        ("dark", "#101018"),
        ("green", "#00ff00"),
        ("magenta", "#ff00ff"),
        ("cyan", "#00ffff"),
        ("checker", checker((380, 380))),
    ]
    hostile = Image.new("RGB", (380 * 3, 380 * len(backgrounds)), "#777777")
    for row, (_, background) in enumerate(backgrounds):
        for col, state in enumerate(STATES):
            hostile.paste(on_background(small[state], background), (col * 380, row * 380))
    hostile.save(AUDIT / "hostile-380-states-v1.png", optimize=True)

    weights = (0.0, 0.25, 0.5, 0.75, 1.0)
    crossfade = Image.new("RGB", (380 * len(weights), 380 * 2), "#17171f")
    for row, state in enumerate(("blink", "roar")):
        for col, weight in enumerate(weights):
            blend = weighted_blend(images["neutral"], images[state], weight).resize(
                (380, 380), Image.Resampling.LANCZOS
            )
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
        state_record: dict[str, object] = {
            "green_dominant_partial_alpha_pixels": int(green_dominant.sum())
        }
        if state != "neutral":
            delta = np.max(
                np.abs(pixels[..., :3].astype(np.int16) - neutral_rgb), axis=2
            )
            changed = (delta > 2) & (alpha_array > 0)
            changed_y, changed_x = np.where(changed)
            state_record.update(
                {
                    "changed_visible_pixels": int(changed.sum()),
                    "changed_visible_percent": float(changed.sum() / (alpha_array > 0).sum() * 100),
                    "changed_bbox": [
                        int(changed_x.min()),
                        int(changed_y.min()),
                        int(changed_x.max() + 1),
                        int(changed_y.max() + 1),
                    ],
                }
            )
        state_stability[state] = state_record
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
        "corner_alpha": [
            int(alpha_array[0, 0]),
            int(alpha_array[0, -1]),
            int(alpha_array[-1, 0]),
            int(alpha_array[-1, -1]),
        ],
        "enclosed_hole_pixels": enclosed_hole_pixels,
        "alpha_sha256": hashlib.sha256(locked_alpha.tobytes()).hexdigest(),
        "state_stability": state_stability,
        "exports": exports,
    }
    (AUDIT / "manifest-v1.json").write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
