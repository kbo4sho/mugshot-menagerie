from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
ANIMAL = ROOT / "design" / "runtime" / "leopard"
CHROMA = ANIMAL / "chroma"
ALPHA = ANIMAL / "alpha"
AUDIT = ANIMAL / "audit"
PUBLIC = ROOT / "public" / "masks" / "leopard"
PAGES = ROOT / "github-pages" / "public" / "masks" / "leopard"
STATES = ("neutral", "blink", "roar")
CANVAS = (1254, 1254)
SCALE = 0.94
WEBP_QUALITY = 95


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rounded_mask(
    size: tuple[int, int], boxes: tuple[tuple[int, int, int, int], ...], radius: int, feather: float
) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for box in boxes:
        draw.rounded_rectangle(box, radius=radius, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(feather))


def localized_rgb(base: Image.Image, edit: Image.Image, mask: Image.Image) -> Image.Image:
    return Image.composite(edit.convert("RGB"), base.convert("RGB"), mask)


def scale_rgba(image: Image.Image) -> Image.Image:
    scaled_size = (round(image.width * SCALE), round(image.height * SCALE))
    scaled = image.convert("RGBA").resize(scaled_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    offset = ((CANVAS[0] - scaled.width) // 2, (CANVAS[1] - scaled.height) // 2)
    canvas.alpha_composite(scaled, offset)
    return canvas


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
    # blend when only one expression channel is active.
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
    CHROMA.mkdir(parents=True, exist_ok=True)
    ALPHA.mkdir(parents=True, exist_ok=True)
    AUDIT.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    PAGES.mkdir(parents=True, exist_ok=True)

    raw_neutral_path = AUDIT / "generated-neutral-v1.png"
    raw_neutral = Image.open(raw_neutral_path).convert("RGB")
    raw_blink = Image.open(AUDIT / "generated-blink-v1.png").convert("RGB")
    raw_roar = Image.open(AUDIT / "generated-roar-v1.png").convert("RGB")
    if raw_neutral.size != CANVAS or raw_blink.size != CANVAS or raw_roar.size != CANVAS:
        raise RuntimeError("All generated masters must be 1254 x 1254")

    # The generated expression frames are used only inside compact facial ROIs.
    # Neutral supplies the entire silhouette, ears, fur field, lighting, and crop.
    blink_mask = rounded_mask(
        CANVAS,
        ((270, 500, 585, 825), (670, 500, 985, 825)),
        radius=115,
        feather=18,
    )
    roar_mask = rounded_mask(
        CANVAS,
        ((480, 790, 775, 1110), (350, 500, 540, 690), (715, 500, 905, 690)),
        radius=54,
        feather=16,
    )
    localized = {
        "neutral": raw_neutral,
        "blink": localized_rgb(raw_neutral, raw_blink, blink_mask),
        "roar": localized_rgb(raw_neutral, raw_roar, roar_mask),
    }

    helper = (
        Path.home()
        / ".codex"
        / "skills"
        / ".system"
        / "imagegen"
        / "scripts"
        / "remove_chroma_key.py"
    )
    extracted = AUDIT / "neutral-extracted-v1.png"
    subprocess.run(
        [
            sys.executable,
            str(helper),
            "--input",
            str(raw_neutral_path),
            "--out",
            str(extracted),
            "--auto-key",
            "border",
            "--soft-matte",
            "--transparent-threshold",
            "12",
            "--opaque-threshold",
            "220",
            "--despill",
            "--force",
        ],
        check=True,
    )
    extracted_neutral = Image.open(extracted).convert("RGBA")
    extracted_rgb = extracted_neutral.convert("RGB")
    extracted_alpha = extracted_neutral.getchannel("A")
    # Prevent even the feathered edge of an expression ROI from touching the
    # keyed silhouette. This makes perimeter RGB as well as alpha identical.
    safe_interior = extracted_alpha.filter(ImageFilter.MinFilter(41))
    state_masks = {
        "blink": ImageChops.multiply(blink_mask, safe_interior),
        "roar": ImageChops.multiply(roar_mask, safe_interior),
    }

    # Start every state from the same despilled neutral, then apply only the
    # expression ROI. This keeps all non-expression RGB pixels deterministic.
    unscaled: dict[str, Image.Image] = {"neutral": extracted_neutral}
    for state, mask in state_masks.items():
        rgb = Image.composite(localized[state], extracted_rgb, mask)
        rgba = rgb.convert("RGBA")
        rgba.putalpha(extracted_alpha)
        unscaled[state] = rgba

    images = {state: scale_rgba(unscaled[state]) for state in STATES}
    locked_alpha = images["neutral"].getchannel("A")
    locked_alpha_hash = hashlib.sha256(locked_alpha.tobytes()).hexdigest()
    for state, image in images.items():
        image.putalpha(locked_alpha)
        image.save(ALPHA / f"{state}-v1.png", optimize=True)
        chroma = Image.new("RGBA", CANVAS, "#00ff00")
        chroma.alpha_composite(image)
        chroma.convert("RGB").save(CHROMA / f"{state}-v1.png", optimize=True)

    exports: dict[str, dict[str, object]] = {}
    runtime_images: dict[str, Image.Image] = {}
    for state, image in images.items():
        target = PUBLIC / f"{state}-v1.webp"
        image.save(
            target,
            "WEBP",
            quality=WEBP_QUALITY,
            alpha_quality=100,
            method=6,
            exact=True,
        )
        pages_target = PAGES / target.name
        pages_target.write_bytes(target.read_bytes())
        decoded = Image.open(target).convert("RGBA")
        runtime_images[state] = decoded
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

    # All runtime-sized evidence decodes the actual shipped WebPs rather than
    # using the larger alpha-master PNGs as a proxy.
    small = {
        state: image.resize((380, 380), Image.Resampling.LANCZOS)
        for state, image in runtime_images.items()
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

    native = Image.new("RGB", (CANVAS[0] * 3, CANVAS[1]), "#101018")
    for col, state in enumerate(STATES):
        native.paste(on_background(images[state], checker(CANVAS, cell=48)), (col * CANVAS[0], 0))
    native.save(AUDIT / "native-states-v1.jpg", quality=92, optimize=True)

    weights = (0.0, 0.25, 0.5, 0.75, 1.0)
    crossfade = Image.new("RGB", (380 * len(weights), 380 * 2), "#17171f")
    for row, state in enumerate(("blink", "roar")):
        for col, weight in enumerate(weights):
            blend = weighted_blend(runtime_images["neutral"], runtime_images[state], weight).resize(
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

    stability: dict[str, dict[str, object]] = {}
    neutral_array = np.asarray(images["neutral"].convert("RGB"), dtype=np.int16)
    for state in ("blink", "roar"):
        state_array = np.asarray(images[state].convert("RGB"), dtype=np.int16)
        delta = np.max(np.abs(state_array - neutral_array), axis=2)
        changed = (delta > 2) & (alpha_array > 0)
        cy, cx = np.where(changed)
        stability[state] = {
            "changed_visible_pixels": int(changed.sum()),
            "changed_visible_percent": float(changed.sum() / (alpha_array > 0).sum() * 100),
            "changed_bbox": [int(cx.min()), int(cy.min()), int(cx.max() + 1), int(cy.max() + 1)],
        }

    metrics = {
        "version": "v1",
        "native_dimensions": list(CANVAS),
        "runtime_dimensions": list(CANVAS),
        "review_dimensions": [380, 380],
        "localized_expression_rois": True,
        "post_key_subject_scale": SCALE,
        "webp_quality": WEBP_QUALITY,
        "alpha_bbox": [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)],
        "alpha_centroid": [float(xs.mean()), float(ys.mean())],
        "padding_px": {
            "left": int(xs.min()),
            "top": int(ys.min()),
            "right": int(CANVAS[0] - 1 - xs.max()),
            "bottom": int(CANVAS[1] - 1 - ys.max()),
        },
        "corner_alpha": {
            "top_left": int(alpha_array[0, 0]),
            "top_right": int(alpha_array[0, -1]),
            "bottom_left": int(alpha_array[-1, 0]),
            "bottom_right": int(alpha_array[-1, -1]),
        },
        "nonzero_alpha_pixels": int((alpha_array > 0).sum()),
        "partial_alpha_pixels": int(partial.sum()),
        "interior_hole_pixels": interior_holes,
        "partial_alpha_green_fringe_pixels": int(green_fringe.sum()),
        "alpha_sha256": locked_alpha_hash,
        "state_stability": stability,
        "exports": exports,
    }
    (AUDIT / "manifest-v1.json").write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
