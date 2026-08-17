from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parents[4]
ZEBRA = ROOT / "design" / "runtime" / "zebra"
ALPHA = ZEBRA / "alpha"
AUDIT = ZEBRA / "audit"
PUBLIC = ROOT / "public" / "masks" / "zebra"
PAGES = ROOT / "github-pages" / "public" / "masks" / "zebra"
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
    if isinstance(background, str):
        base = Image.new("RGBA", foreground.size, background)
    else:
        base = background.convert("RGBA")
    return Image.alpha_composite(base, foreground).convert("RGB")


def weighted_blend(a: Image.Image, b: Image.Image, weight: float) -> Image.Image:
    # Premultiplied-alpha weighted sum mirrors the runtime's copy + lighter
    # expression blending for one active channel.
    aa = np.asarray(a.convert("RGBA"), dtype=np.float32) / 255.0
    bb = np.asarray(b.convert("RGBA"), dtype=np.float32) / 255.0
    a_alpha = aa[..., 3:4]
    b_alpha = bb[..., 3:4]
    out_alpha = a_alpha * (1.0 - weight) + b_alpha * weight
    out_rgb_p = aa[..., :3] * a_alpha * (1.0 - weight) + bb[..., :3] * b_alpha * weight
    out_rgb = np.divide(
        out_rgb_p,
        out_alpha,
        out=np.zeros_like(out_rgb_p),
        where=out_alpha > 1e-8,
    )
    out = np.concatenate((out_rgb, out_alpha), axis=2)
    return Image.fromarray(np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8))


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    PAGES.mkdir(parents=True, exist_ok=True)

    images = {state: Image.open(ALPHA / f"{state}-v1.png").convert("RGBA") for state in STATES}
    locked_alpha = images["neutral"].getchannel("A")
    locked_alpha_hash = hashlib.sha256(locked_alpha.tobytes()).hexdigest()
    for state, image in images.items():
        if ImageChops.difference(image.getchannel("A"), locked_alpha).getbbox() is not None:
            raise RuntimeError(f"{state}: alpha differs from neutral")
        image.putalpha(locked_alpha)
        image.save(ALPHA / f"{state}-v1.png", optimize=True)
        images[state] = image

    exports: dict[str, dict[str, object]] = {}
    decoded_images: dict[str, Image.Image] = {}
    for state, image in images.items():
        target = PUBLIC / f"{state}-v1.webp"
        image.save(target, "WEBP", quality=95, alpha_quality=100, method=6, exact=True)
        pages_target = PAGES / target.name
        pages_target.write_bytes(target.read_bytes())

        decoded = Image.open(target).convert("RGBA")
        decoded_images[state] = decoded
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
            "decoded_alpha_matches_master": decoded_alpha_hash == locked_alpha_hash,
        }

    small = {
        state: image.resize((380, 380), Image.Resampling.LANCZOS)
        for state, image in decoded_images.items()
    }
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

    native = Image.new(
        "RGB",
        (decoded_images["neutral"].width * 3, decoded_images["neutral"].height),
        "#101018",
    )
    for col, state in enumerate(STATES):
        native.paste(
            on_background(decoded_images[state], checker(decoded_images[state].size, cell=48)),
            (col * decoded_images[state].width, 0),
        )
    native.save(AUDIT / "native-states-v1.jpg", quality=92, optimize=True)

    weights = (0.0, 0.25, 0.5, 0.75, 1.0)
    crossfade = Image.new("RGB", (380 * len(weights), 380 * 2), "#17171f")
    for row, state in enumerate(("blink", "roar")):
        for col, weight in enumerate(weights):
            blend = weighted_blend(decoded_images["neutral"], decoded_images[state], weight).resize(
                (380, 380), Image.Resampling.LANCZOS
            )
            crossfade.paste(on_background(blend, checker((380, 380))), (col * 380, row * 380))
    crossfade.save(AUDIT / "copy-lighter-crossfades-380-v1.png", optimize=True)

    alpha_array = np.asarray(locked_alpha)
    ys, xs = np.where(alpha_array > 0)
    transparency = Image.fromarray(np.where(alpha_array == 0, 255, 0).astype(np.uint8)).copy()
    ImageDraw.floodfill(transparency, (0, 0), 128, thresh=0)
    interior_holes = int((np.asarray(transparency) == 255).sum())
    neutral_rgb = np.asarray(images["neutral"].convert("RGB"), dtype=np.int16)
    partial = (alpha_array > 0) & (alpha_array < 255)
    green_fringe = partial & (neutral_rgb[..., 1] > neutral_rgb[..., 0] * 1.15) & (
        neutral_rgb[..., 1] > neutral_rgb[..., 2] * 1.15
    )
    localization: dict[str, dict[str, object]] = {}
    for state in ("blink", "roar"):
        mask = np.asarray(Image.open(AUDIT / f"{state}-localization-mask-v1.png").convert("L"))
        state_rgb = np.asarray(images[state].convert("RGB"), dtype=np.int16)
        delta = np.max(np.abs(state_rgb - neutral_rgb), axis=2)
        changed_y, changed_x = np.where(delta > 0)
        outside = delta[mask == 0]
        decoded_rgb = np.asarray(decoded_images[state].convert("RGB"), dtype=np.int16)
        decoded_neutral_rgb = np.asarray(decoded_images["neutral"].convert("RGB"), dtype=np.int16)
        decoded_delta = np.max(np.abs(decoded_rgb - decoded_neutral_rgb), axis=2)
        stripe_like = (
            (0.299 * decoded_neutral_rgb[..., 0]
             + 0.587 * decoded_neutral_rgb[..., 1]
             + 0.114 * decoded_neutral_rgb[..., 2])
            < 130
        ) & (np.asarray(decoded_images["neutral"].getchannel("A")) > 200) & (mask == 0)
        decoded_stripe_delta = decoded_delta[stripe_like]
        localization[state] = {
            "master_changed_bbox": [
                int(changed_x.min()),
                int(changed_y.min()),
                int(changed_x.max() + 1),
                int(changed_y.max() + 1),
            ],
            "master_changed_pixels": int((delta > 0).sum()),
            "master_changed_pixels_outside_localization_mask": int((outside > 0).sum()),
            "master_max_delta_outside_localization_mask": int(outside.max()),
            "decoded_q95_stripe_like_mean_delta_outside_roi": float(decoded_stripe_delta.mean()),
            "decoded_q95_stripe_like_max_delta_outside_roi": int(decoded_stripe_delta.max()),
        }
    chroma_border: dict[str, dict[str, object]] = {}
    for state in STATES:
        chroma = np.asarray(Image.open(ZEBRA / "chroma" / f"{state}-v1.png").convert("RGB"))
        border = np.concatenate((chroma[0], chroma[-1], chroma[:, 0], chroma[:, -1]), axis=0)
        unique = np.unique(border, axis=0)
        chroma_border[state] = {
            "unique_border_colors": int(len(unique)),
            "exact_00ff00": bool(len(unique) == 1 and np.array_equal(unique[0], [0, 255, 0])),
        }
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
        "corner_alpha": {
            "top_left": int(alpha_array[0, 0]),
            "top_right": int(alpha_array[0, -1]),
            "bottom_left": int(alpha_array[-1, 0]),
            "bottom_right": int(alpha_array[-1, -1]),
        },
        "nonzero_alpha_pixels": int((alpha_array > 0).sum()),
        "partial_alpha_pixels": int(((alpha_array > 0) & (alpha_array < 255)).sum()),
        "interior_hole_pixels": interior_holes,
        "partial_alpha_green_fringe_pixels": int(green_fringe.sum()),
        "alpha_sha256": locked_alpha_hash,
        "chroma_border": chroma_border,
        "localization": localization,
        "exports": exports,
    }
    (AUDIT / "manifest-v1.json").write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
