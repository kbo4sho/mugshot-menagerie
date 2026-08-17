from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import export_and_audit as v1


ROOT = Path(__file__).resolve().parents[4]
UNICORN = ROOT / "design" / "runtime" / "unicorn"
CHROMA = UNICORN / "chroma"
ALPHA = UNICORN / "alpha"
AUDIT = UNICORN / "audit"
PUBLIC = ROOT / "public" / "masks" / "unicorn"
PAGES = ROOT / "github-pages" / "public" / "masks" / "unicorn"
STATES = ("neutral", "blink", "roar")
CANVAS = (1254, 1254)
VERSION = "v2"
SCALE = 0.92
WEBP_QUALITY = 95


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    generated = {
        "neutral": Image.open(AUDIT / "generated-neutral-v1.png").convert("RGB"),
        "blink": Image.open(AUDIT / "generated-blink-v1.png").convert("RGB"),
        "roar": Image.open(AUDIT / "generated-roar-v1.png").convert("RGB"),
    }
    generated["roar"], cavity_mask = v1.normalize_roar_cavity(generated["roar"])
    cavity_mask.save(AUDIT / "roar-cavity-normalization-mask-v2.png", optimize=True)

    blink_mask = v1.rounded_mask(
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
    roar_mask = v1.rounded_mask(
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
        "blink": v1.localized_rgb(generated["neutral"], generated["blink"], blink_mask),
        "roar": v1.localized_rgb(generated["neutral"], generated["roar"], roar_mask),
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
    extracted_path = AUDIT / "neutral-extracted-v2.png"
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
    extracted_array = np.asarray(Image.open(extracted_path).convert("RGBA")).copy()
    raw_array = np.asarray(generated["neutral"])
    alpha_before = extracted_array[..., 3].copy()

    # v1 stopped at x=700/y=430. The mint forelock curves left and continues
    # below that boundary while remaining entirely inside the opaque face.
    # Extend only this known interior material ROI; require already-detected
    # subject alpha and pastel subject RGB so the outer silhouette cannot grow.
    mint_roi = np.zeros((CANVAS[1], CANVAS[0]), dtype=bool)
    mint_roi[270:550, 650:820] = True
    pastel_subject = (
        raw_array[..., 0].astype(np.int16) + raw_array[..., 2].astype(np.int16)
    ) > 220
    mint_repair = (
        mint_roi
        & (alpha_before > 8)
        & (alpha_before < 250)
        & pastel_subject
    )
    extracted_array[mint_repair, :3] = raw_array[mint_repair]
    extracted_array[mint_repair, 3] = 255
    extracted_neutral = Image.fromarray(extracted_array)
    extracted_neutral.save(extracted_path, optimize=True)
    Image.fromarray(mint_repair.astype(np.uint8) * 255).save(
        AUDIT / "mint-matte-repair-mask-v2.png", optimize=True
    )

    extracted_rgb = extracted_neutral.convert("RGB")
    extracted_alpha = extracted_neutral.getchannel("A")
    safe_interior = extracted_alpha.filter(ImageFilter.MinFilter(41))
    state_masks = {
        "blink": ImageChops.multiply(blink_mask, safe_interior),
        "roar": ImageChops.multiply(roar_mask, safe_interior),
    }

    unscaled: dict[str, Image.Image] = {"neutral": extracted_neutral}
    for state in ("blink", "roar"):
        rgb = Image.composite(localized[state], extracted_rgb, state_masks[state])
        rgba = rgb.convert("RGBA")
        rgba.putalpha(extracted_alpha)
        unscaled[state] = rgba

    images = {state: v1.scale_rgba(unscaled[state]) for state in STATES}
    locked_alpha = images["neutral"].getchannel("A")
    locked_alpha_hash = hashlib.sha256(locked_alpha.tobytes()).hexdigest()
    for state, image in images.items():
        image.putalpha(locked_alpha)
        image.save(ALPHA / f"{state}-{VERSION}.png", optimize=True)
        chroma = Image.new("RGBA", CANVAS, "#00ff00")
        chroma.alpha_composite(image)
        chroma.convert("RGB").save(CHROMA / f"{state}-{VERSION}.png", optimize=True)

    exports: dict[str, dict[str, object]] = {}
    runtime_images: dict[str, Image.Image] = {}
    for state, image in images.items():
        target = PUBLIC / f"{state}-{VERSION}.webp"
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
    backgrounds: list[Image.Image | str] = [
        "#ffffff",
        "#101018",
        "#00ff00",
        "#ff00ff",
        "#00ffff",
        v1.checker((380, 380)),
    ]
    hostile = Image.new("RGB", (380 * 3, 380 * len(backgrounds)), "#777777")
    for row, background in enumerate(backgrounds):
        for col, state in enumerate(STATES):
            hostile.paste(v1.on_background(small_380[state], background), (col * 380, row * 380))
    hostile.save(AUDIT / "hostile-380-states-v2.png", optimize=True)

    scale_sheet = Image.new("RGB", (380 * 3, 500), "#101018")
    for col, state in enumerate(STATES):
        scale_sheet.paste(
            v1.on_background(small_380[state], v1.checker((380, 380))),
            (col * 380, 0),
        )
        scale_sheet.paste(
            v1.on_background(small_96[state], v1.checker((96, 96), cell=12)),
            (col * 380 + 142, 394),
        )
    scale_sheet.save(AUDIT / "states-380-and-96-v2.png", optimize=True)

    v1_runtime = Image.open(PUBLIC / "neutral-v1.webp").convert("RGBA").resize(
        (380, 380), Image.Resampling.LANCZOS
    )
    comparison_backgrounds: list[Image.Image | str] = [
        "#101018",
        "#00ff00",
        "#ff00ff",
        "#00ffff",
        v1.checker((380, 380)),
    ]
    compare = Image.new("RGB", (320 * 2, 360 * len(comparison_backgrounds)), "#101018")
    crop_box = (178, 102, 258, 192)
    for row, background in enumerate(comparison_backgrounds):
        for col, image in enumerate((v1_runtime, small_380["neutral"])):
            crop = v1.on_background(image, background).crop(crop_box)
            crop = crop.resize((320, 360), Image.Resampling.NEAREST)
            compare.paste(crop, (col * 320, row * 360))
    compare.save(AUDIT / "mint-lock-v1-v2-hostile-closeups-380.png", optimize=True)

    weights = (0.0, 0.25, 0.5, 0.75, 1.0)
    crossfade = Image.new("RGB", (380 * len(weights), 380 * 2), "#17171f")
    for row, state in enumerate(("blink", "roar")):
        for col, weight in enumerate(weights):
            blend = v1.weighted_blend(
                (runtime_images["neutral"], runtime_images[state]),
                (1.0 - weight, weight),
            ).resize((380, 380), Image.Resampling.LANCZOS)
            crossfade.paste(
                v1.on_background(blend, v1.checker((380, 380))),
                (col * 380, row * 380),
            )
    crossfade.save(AUDIT / "copy-lighter-crossfades-380-v2.png", optimize=True)

    canonical_native = Image.new("L", CANVAS, 0)
    ImageDraw.Draw(canonical_native).ellipse((330, 360, 924, 1030), fill=255)
    canonical_native_array = np.asarray(canonical_native) > 0
    alpha_native = np.asarray(locked_alpha)
    canonical_380 = Image.new("L", (380, 380), 0)
    ImageDraw.Draw(canonical_380).ellipse((100, 109, 280, 312), fill=255)
    canonical_380_array = np.asarray(canonical_380) > 0
    alpha_380 = np.asarray(small_380["neutral"].getchannel("A"))

    v1_alpha = np.asarray(Image.open(ALPHA / "neutral-v1.png").convert("RGBA"))[..., 3]
    alpha_delta = alpha_native.astype(np.int16) - v1_alpha.astype(np.int16)
    changed = alpha_delta != 0
    changed_y, changed_x = np.where(changed)
    outer_safety = np.zeros_like(changed)
    outer_safety[285:570, 630:825] = True
    new_nonzero = (v1_alpha == 0) & (alpha_native > 0)
    master_changes: dict[str, dict[str, object]] = {}
    for state in STATES:
        previous = np.asarray(Image.open(ALPHA / f"{state}-v1.png").convert("RGBA"))
        current = np.asarray(images[state].convert("RGBA"))
        state_changed = np.any(previous != current, axis=2)
        state_y, state_x = np.where(state_changed)
        master_changes[state] = {
            "changed_rgba_pixels": int(state_changed.sum()),
            "changed_bbox": [
                int(state_x.min()),
                int(state_y.min()),
                int(state_x.max() + 1),
                int(state_y.max() + 1),
            ],
            "changed_pixels_outside_inner_crown_safety_box": int(
                (state_changed & ~outer_safety).sum()
            ),
        }

    partial = (alpha_native > 0) & (alpha_native < 255)
    neutral_rgb = np.asarray(images["neutral"].convert("RGB"), dtype=np.int16)
    green_flags = partial & (neutral_rgb[..., 1] > neutral_rgb[..., 0] * 1.15) & (
        neutral_rgb[..., 1] > neutral_rgb[..., 2] * 1.15
    )
    green_y, green_x = np.where(green_flags)

    alpha_proof = Image.new("RGB", (380 * 3, 380), "#101018")
    v1_alpha_380 = np.asarray(v1_runtime.getchannel("A"))
    alpha_proof.paste(Image.fromarray(v1_alpha_380).convert("RGB"), (0, 0))
    alpha_proof.paste(Image.fromarray(alpha_380).convert("RGB"), (380, 0))
    overlay = np.zeros((380, 380, 3), dtype=np.uint8)
    overlay[canonical_380_array] = (255, 255, 255)
    overlay[canonical_380_array & (alpha_380 < 250)] = (255, 0, 0)
    alpha_proof.paste(Image.fromarray(overlay), (760, 0))
    alpha_proof.save(AUDIT / "canonical-face-alpha-proof-380-v2.png", optimize=True)

    metrics = {
        "version": VERSION,
        "source_version": "v1 generated sources and localized expressions",
        "native_dimensions": list(CANVAS),
        "runtime_dimensions": list(CANVAS),
        "review_dimensions": [380, 380],
        "post_key_subject_scale": SCALE,
        "webp_quality": WEBP_QUALITY,
        "mint_repair_source_pixels": int(mint_repair.sum()),
        "mint_repair_source_bbox": [650, 270, 820, 550],
        "mint_repair_residual_partial_source_pixels": int(
            (mint_roi & (extracted_array[..., 3] < 250) & (extracted_array[..., 3] > 8) & pastel_subject).sum()
        ),
        "canonical_face_forehead_native": {
            "mask_pixels": int(canonical_native_array.sum()),
            "alpha_gte_250_pixels": int(((alpha_native >= 250) & canonical_native_array).sum()),
            "alpha_gte_250_ratio": float((alpha_native[canonical_native_array] >= 250).mean()),
            "minimum_alpha": int(alpha_native[canonical_native_array].min()),
        },
        "canonical_face_forehead_380": {
            "mask_pixels": int(canonical_380_array.sum()),
            "alpha_gte_250_pixels": int(((alpha_380 >= 250) & canonical_380_array).sum()),
            "alpha_gte_250_ratio": float((alpha_380[canonical_380_array] >= 250).mean()),
            "minimum_alpha": int(alpha_380[canonical_380_array].min()),
        },
        "v1_to_v2_alpha_change": {
            "changed_pixels": int(changed.sum()),
            "changed_bbox": [
                int(changed_x.min()),
                int(changed_y.min()),
                int(changed_x.max() + 1),
                int(changed_y.max() + 1),
            ],
            "changed_pixels_outside_inner_crown_safety_box": int((changed & ~outer_safety).sum()),
            "new_nonzero_alpha_pixels": int(new_nonzero.sum()),
            "maximum_alpha_increase": int(alpha_delta.max()),
            "minimum_alpha_change": int(alpha_delta.min()),
        },
        "v1_to_v2_master_changes": master_changes,
        "alpha": v1.alpha_metrics(locked_alpha),
        "partial_alpha_green_flags": {
            "pixels": int(green_flags.sum()),
            "alpha_minimum": int(alpha_native[green_flags].min()),
            "alpha_maximum": int(alpha_native[green_flags].max()),
            "pixels_alpha_lte_64": int((green_flags & (alpha_native <= 64)).sum()),
            "percent_alpha_lte_64": float(
                (green_flags & (alpha_native <= 64)).sum() / green_flags.sum() * 100
            ),
            "pixels_inside_canonical_face_forehead": int(
                (green_flags & canonical_native_array).sum()
            ),
            "bbox": [
                int(green_x.min()),
                int(green_y.min()),
                int(green_x.max() + 1),
                int(green_y.max() + 1),
            ],
        },
        "shared_alpha_sha256": locked_alpha_hash,
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
        "final_chroma_exterior_is_exact_00ff00": all(
            np.all(
                np.asarray(Image.open(CHROMA / f"{state}-{VERSION}.png").convert("RGB"))[
                    alpha_native == 0
                ]
                == np.array([0, 255, 0]),
                axis=1,
            ).all()
            for state in STATES
        ),
        "exports": exports,
    }
    (AUDIT / "manifest-v2.json").write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
