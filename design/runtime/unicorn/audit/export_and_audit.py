from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
UNICORN = ROOT / "design" / "runtime" / "unicorn"
CHROMA = UNICORN / "chroma"
ALPHA = UNICORN / "alpha"
AUDIT = UNICORN / "audit"
PUBLIC = ROOT / "public" / "masks" / "unicorn"
PAGES = ROOT / "github-pages" / "public" / "masks" / "unicorn"
STATES = ("neutral", "blink", "roar")
CANVAS = (1254, 1254)
SCALE = 0.92
WEBP_QUALITY = 95


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rounded_mask(
    size: tuple[int, int],
    boxes: tuple[tuple[int, int, int, int], ...],
    radius: int,
    feather: float,
) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for box in boxes:
        draw.rounded_rectangle(box, radius=radius, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(feather))


def localized_rgb(base: Image.Image, edit: Image.Image, mask: Image.Image) -> Image.Image:
    return Image.composite(edit.convert("RGB"), base.convert("RGB"), mask)


def normalize_roar_cavity(image: Image.Image) -> tuple[Image.Image, Image.Image]:
    array = np.asarray(image.convert("RGB")).astype(np.float32)
    yy, xx = np.mgrid[0 : image.height, 0 : image.width]
    ellipse = ((xx - 627.0) / 38.0) ** 2 + ((yy - 1045.0) / 47.0) ** 2
    luma = array[..., 0] * 0.2126 + array[..., 1] * 0.7152 + array[..., 2] * 0.0722
    cavity = (ellipse < 1.0) & (luma < 105.0)
    vertical = np.clip((yy - 1008.0) / 74.0, 0.0, 1.0)
    target_top = np.array([54.0, 7.0, 20.0])
    target_bottom = np.array([83.0, 16.0, 38.0])
    target = target_top + vertical[..., None] * (target_bottom - target_top)
    # Preserve the model-rendered soft lip edge; normalize the dark cavity core.
    strength = np.clip((105.0 - luma) / 48.0, 0.0, 1.0) * cavity
    array = array * (1.0 - strength[..., None]) + target * strength[..., None]
    return (
        Image.fromarray(np.clip(array + 0.5, 0, 255).astype(np.uint8)),
        Image.fromarray(np.clip(strength * 255.0 + 0.5, 0, 255).astype(np.uint8)),
    )


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


def weighted_blend(images: tuple[Image.Image, ...], weights: tuple[float, ...]) -> Image.Image:
    arrays = [np.asarray(image.convert("RGBA"), dtype=np.float32) / 255.0 for image in images]
    alpha = sum(weight * array[..., 3:4] for weight, array in zip(weights, arrays))
    rgb_p = sum(
        weight * array[..., :3] * array[..., 3:4]
        for weight, array in zip(weights, arrays)
    )
    rgb = np.divide(rgb_p, alpha, out=np.zeros_like(rgb_p), where=alpha > 1e-8)
    out = np.concatenate((rgb, alpha), axis=2)
    return Image.fromarray(np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8))


def alpha_metrics(alpha: Image.Image) -> dict[str, object]:
    array = np.asarray(alpha)
    ys, xs = np.where(array > 8)
    # Treat <=32 as background for a useful topology check. Exact-zero pixels
    # can be isolated behind a one-pixel Lanczos antialias ring after scaling
    # even though no visible transparent hole exists.
    transparency = Image.fromarray(np.where(array <= 32, 255, 0).astype(np.uint8)).copy()
    ImageDraw.floodfill(transparency, (0, 0), 128, thresh=0)
    bbox_width = int(xs.max() + 1 - xs.min())
    bbox_height = int(ys.max() + 1 - ys.min())
    return {
        "bbox_alpha_gt_8": [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)],
        "bbox_canvas_coverage_percent": [
            float(bbox_width / CANVAS[0] * 100),
            float(bbox_height / CANVAS[1] * 100),
        ],
        "centroid_nonzero_alpha": [float(xs.mean()), float(ys.mean())],
        "padding_px": {
            "left": int(xs.min()),
            "top": int(ys.min()),
            "right": int(CANVAS[0] - 1 - xs.max()),
            "bottom": int(CANVAS[1] - 1 - ys.max()),
        },
        "corner_alpha": [int(array[0, 0]), int(array[0, -1]), int(array[-1, 0]), int(array[-1, -1])],
        "nonzero_alpha_pixels": int((array > 0).sum()),
        "partial_alpha_pixels": int(((array > 0) & (array < 255)).sum()),
        "interior_hole_pixels_alpha_le_32": int((np.asarray(transparency) == 255).sum()),
    }


def main() -> None:
    for directory in (CHROMA, ALPHA, AUDIT, PUBLIC, PAGES):
        directory.mkdir(parents=True, exist_ok=True)

    generated = {
        "neutral": Image.open(AUDIT / "generated-neutral-v1.png").convert("RGB"),
        "blink": Image.open(AUDIT / "generated-blink-v1.png").convert("RGB"),
        "roar": Image.open(AUDIT / "generated-roar-v1.png").convert("RGB"),
    }
    if any(image.size != CANVAS for image in generated.values()):
        raise RuntimeError("All generated masters must be 1254 x 1254")
    generated["roar"], cavity_mask = normalize_roar_cavity(generated["roar"])
    cavity_mask.save(AUDIT / "roar-cavity-normalization-mask-v1.png", optimize=True)

    blink_mask = rounded_mask(
        CANVAS,
        (
            (260, 625, 540, 910),
            (714, 625, 994, 910),
            (300, 525, 460, 650),
            (794, 525, 954, 650),
        ),
        radius=64,
        feather=12,
    )
    roar_mask = rounded_mask(
        CANVAS,
        (
            (550, 965, 704, 1110),
            (300, 525, 460, 650),
            (794, 525, 954, 650),
        ),
        radius=44,
        feather=11,
    )
    localized = {
        "neutral": generated["neutral"],
        "blink": localized_rgb(generated["neutral"], generated["blink"], blink_mask),
        "roar": localized_rgb(generated["neutral"], generated["roar"], roar_mask),
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
    extracted_path = AUDIT / "neutral-extracted-v1.png"
    subprocess.run(
        [
            sys.executable,
            str(helper),
            "--input",
            str(AUDIT / "generated-neutral-v1.png"),
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
            "--force",
        ],
        check=True,
    )
    extracted_neutral = Image.open(extracted_path).convert("RGBA")
    # The mint crown lock is intentionally close to the key hue. Restore only
    # already-detected subject pixels in its compact interior ROI from the raw
    # source so chroma despill cannot turn that pastel lock gray/transparent.
    extracted_array = np.asarray(extracted_neutral).copy()
    raw_array = np.asarray(generated["neutral"])
    repair_roi = np.zeros((CANVAS[1], CANVAS[0]), dtype=bool)
    repair_roi[270:430, 700:820] = True
    alpha_before_repair = extracted_array[..., 3]
    pastel_subject = (raw_array[..., 0].astype(np.int16) + raw_array[..., 2].astype(np.int16)) > 220
    mint_repair = repair_roi & (alpha_before_repair > 8) & (alpha_before_repair < 250) & pastel_subject
    extracted_array[mint_repair, :3] = raw_array[mint_repair]
    extracted_array[mint_repair, 3] = 255
    extracted_neutral = Image.fromarray(extracted_array)
    extracted_neutral.save(extracted_path, optimize=True)
    Image.fromarray(mint_repair.astype(np.uint8) * 255).save(
        AUDIT / "mint-matte-repair-mask-v1.png", optimize=True
    )
    extracted_rgb = extracted_neutral.convert("RGB")
    extracted_alpha = extracted_neutral.getchannel("A")

    safe_interior = extracted_alpha.filter(ImageFilter.MinFilter(41))
    state_masks = {
        "blink": ImageChops.multiply(blink_mask, safe_interior),
        "roar": ImageChops.multiply(roar_mask, safe_interior),
    }
    blink_mask.save(AUDIT / "blink-localization-mask-v1.png", optimize=True)
    roar_mask.save(AUDIT / "roar-localization-mask-v1.png", optimize=True)

    unscaled: dict[str, Image.Image] = {"neutral": extracted_neutral}
    for state in ("blink", "roar"):
        rgb = Image.composite(localized[state], extracted_rgb, state_masks[state])
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
            "dimensions": list(decoded.size),
            "bytes": target.stat().st_size,
            "sha256": sha256(target),
            "pages_sha256": sha256(pages_target),
            "pages_byte_equal": target.read_bytes() == pages_target.read_bytes(),
            "has_alph_chunk": b"ALPH" in target.read_bytes(),
            "decoded_alpha_sha256": decoded_alpha_hash,
            "decoded_alpha_matches_master": decoded_alpha_hash == locked_alpha_hash,
        }

    small_380 = {
        state: image.resize((380, 380), Image.Resampling.LANCZOS)
        for state, image in runtime_images.items()
    }
    small_96 = {
        state: image.resize((96, 96), Image.Resampling.LANCZOS)
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
            hostile.paste(on_background(small_380[state], background), (col * 380, row * 380))
    hostile.save(AUDIT / "hostile-380-states-v1.png", optimize=True)

    scale_sheet = Image.new("RGB", (380 * 3, 500), "#101018")
    for col, state in enumerate(STATES):
        scale_sheet.paste(on_background(small_380[state], checker((380, 380))), (col * 380, 0))
        thumb_bg = checker((96, 96), cell=12)
        scale_sheet.paste(on_background(small_96[state], thumb_bg), (col * 380 + 142, 394))
    scale_sheet.save(AUDIT / "states-380-and-96-v1.png", optimize=True)

    native = Image.new("RGB", (CANVAS[0] * 3, CANVAS[1]), "#101018")
    for col, state in enumerate(STATES):
        native.paste(on_background(images[state], checker(CANVAS, cell=48)), (col * CANVAS[0], 0))
    native.save(AUDIT / "native-states-v1.jpg", quality=92, optimize=True)

    weights = (0.0, 0.25, 0.5, 0.75, 1.0)
    crossfade = Image.new("RGB", (380 * len(weights), 380 * 3), "#17171f")
    for row, state in enumerate(("blink", "roar")):
        for col, weight in enumerate(weights):
            blend = weighted_blend(
                (runtime_images["neutral"], runtime_images[state]),
                (1.0 - weight, weight),
            ).resize((380, 380), Image.Resampling.LANCZOS)
            crossfade.paste(on_background(blend, checker((380, 380))), (col * 380, row * 380))
    for col, weight in enumerate(weights):
        blink_weight = weight * (1.0 - weight)
        neutral_weight = (1.0 - weight) * (1.0 - weight)
        blend = weighted_blend(
            (runtime_images["neutral"], runtime_images["blink"], runtime_images["roar"]),
            (neutral_weight, blink_weight, weight),
        ).resize((380, 380), Image.Resampling.LANCZOS)
        crossfade.paste(on_background(blend, checker((380, 380))), (col * 380, 760))
    crossfade.save(AUDIT / "copy-lighter-crossfades-380-v1.png", optimize=True)

    matte_sheet = Image.new("RGB", (320 * 4, 320 * 2), "#111118")
    crop_boxes = ((460, 45, 795, 400), (70, 60, 410, 420), (845, 60, 1185, 420), (60, 790, 1190, 1205))
    matte_backgrounds = ("#ffffff", "#101018")
    for row, background in enumerate(matte_backgrounds):
        composited = on_background(images["neutral"], background)
        for col, box in enumerate(crop_boxes):
            crop = composited.crop(box)
            crop.thumbnail((300, 300), Image.Resampling.LANCZOS)
            matte_sheet.paste(crop, (col * 320 + (320 - crop.width) // 2, row * 320 + (320 - crop.height) // 2))
    matte_sheet.save(AUDIT / "horn-mane-matte-closeups-v1.png", optimize=True)

    mouth_sheet = Image.new("RGB", (420 * 3, 330 * 2), "#101018")
    for col, state in enumerate(STATES):
        native_crop = on_background(images[state], checker(CANVAS, cell=48)).crop((430, 790, 824, 1130))
        native_crop.thumbnail((394, 310), Image.Resampling.LANCZOS)
        mouth_sheet.paste(native_crop, (col * 420 + 13, 10))
        runtime_crop = on_background(small_96[state], checker((96, 96), cell=12)).crop((26, 57, 70, 92))
        runtime_crop = runtime_crop.resize((352, 280), Image.Resampling.NEAREST)
        mouth_sheet.paste(runtime_crop, (col * 420 + 34, 350))
    mouth_sheet.save(AUDIT / "mouth-semantics-native-and-96-v1.png", optimize=True)

    alpha_array = np.asarray(locked_alpha)
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
        # Bounding boxes below intentionally prove changes stayed inside compact facial regions.
        stability[state] = {
            "changed_visible_pixels": int(changed.sum()),
            "changed_visible_percent": float(changed.sum() / (alpha_array > 0).sum() * 100),
            "changed_bbox": [int(cx.min()), int(cy.min()), int(cx.max() + 1), int(cy.max() + 1)],
            "max_rgb_delta": int(delta.max()),
        }

    metrics = {
        "version": "v1",
        "native_dimensions": list(CANVAS),
        "runtime_dimensions": list(CANVAS),
        "review_dimensions": [380, 380],
        "localized_expression_rois": True,
        "post_key_subject_scale": SCALE,
        "webp_quality": WEBP_QUALITY,
        "alpha": alpha_metrics(locked_alpha),
        "partial_alpha_green_fringe_pixels": int(green_fringe.sum()),
        "mint_matte_repair_pixels": int(mint_repair.sum()),
        "final_chroma_exterior_is_exact_00ff00": all(
            np.all(
                np.asarray(Image.open(CHROMA / f"{state}-v1.png").convert("RGB"))[alpha_array == 0]
                == np.array([0, 255, 0]),
                axis=1,
            ).all()
            for state in STATES
        ),
        "alpha_sha256": locked_alpha_hash,
        "state_alpha_hashes": {
            state: hashlib.sha256(images[state].getchannel("A").tobytes()).hexdigest()
            for state in STATES
        },
        "state_alpha_hashes_identical": len(
            {
                hashlib.sha256(images[state].getchannel("A").tobytes()).hexdigest()
                for state in STATES
            }
        )
        == 1,
        "state_stability": stability,
        "exports": exports,
    }
    (AUDIT / "manifest-v1.json").write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
