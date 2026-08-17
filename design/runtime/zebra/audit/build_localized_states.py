from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
ZEBRA = ROOT / "design" / "runtime" / "zebra"
CHROMA = ZEBRA / "chroma"
ALPHA = ZEBRA / "alpha"
AUDIT = ZEBRA / "audit"
SOURCES = AUDIT / "imagegen"


def feathered_mask(
    size: tuple[int, int],
    ellipses: list[tuple[int, int, int, int]],
    blur: int,
) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for box in ellipses:
        draw.ellipse(box, fill=255)
    # Feather inward so the expression island blends smoothly while every
    # pixel outside the authored ROI stays bit-identical to neutral.
    return ImageChops.multiply(mask.filter(ImageFilter.GaussianBlur(blur)), mask)


def repair_interior_holes(image: Image.Image) -> tuple[Image.Image, int]:
    rgba = np.asarray(image.convert("RGBA")).copy()
    alpha = rgba[..., 3]
    transparency = Image.fromarray(np.where(alpha == 0, 255, 0).astype(np.uint8)).copy()
    ImageDraw.floodfill(transparency, (0, 0), 128, thresh=0)
    hole_y, hole_x = np.where(np.asarray(transparency) == 255)
    for y, x in zip(hole_y, hole_x):
        y0, y1 = max(0, y - 1), min(rgba.shape[0], y + 2)
        x0, x1 = max(0, x - 1), min(rgba.shape[1], x + 2)
        neighborhood = rgba[y0:y1, x0:x1]
        visible = neighborhood[neighborhood[..., 3] > 0]
        if visible.size == 0:
            raise RuntimeError(f"Cannot repair isolated alpha hole at {(int(x), int(y))}")
        rgba[y, x, :3] = np.median(visible[:, :3], axis=0).astype(np.uint8)
        rgba[y, x, 3] = visible[:, 3].max()
    return Image.fromarray(rgba), int(len(hole_x))


def main() -> None:
    neutral_chroma = Image.open(CHROMA / "neutral-v1.png").convert("RGB")
    neutral_alpha, repaired_holes = repair_interior_holes(
        Image.open(ALPHA / "neutral-v1.png").convert("RGBA")
    )
    neutral_alpha.save(ALPHA / "neutral-v1.png", optimize=True)
    exact_green = Image.new("RGBA", neutral_alpha.size, (0, 255, 0, 255))
    Image.alpha_composite(exact_green, neutral_alpha).convert("RGB").save(
        CHROMA / "neutral-v1.png", optimize=True
    )
    repair_receipt = AUDIT / "alpha-hole-repair-v1.txt"
    if repaired_holes or not repair_receipt.exists():
        repair_receipt.write_text(
            f"Repaired enclosed fully transparent pixels: {repaired_holes}\n"
        )
    blink_generated = Image.open(SOURCES / "blink-v1.generated.png").convert("RGB")
    roar_generated = Image.open(SOURCES / "roar-v1.generated.png").convert("RGB")

    if not (
        neutral_chroma.size
        == neutral_alpha.size
        == blink_generated.size
        == roar_generated.size
    ):
        raise RuntimeError("Zebra sources must share one native canvas")

    # These two islands cover the original open eyes and the generated happy
    # lash arcs, while blending back into the locked neutral face well before
    # any stripe, cheek, ear, mane, or silhouette boundary.
    blink_mask = feathered_mask(
        neutral_chroma.size,
        [
            (285, 560, 575, 865),
            (679, 560, 969, 865),
        ],
        blur=10,
    )

    # The roar edit is deliberately mouth-only. The generated source retained
    # the neutral eyes and did not add a distinct brow shape, so importing any
    # larger region would create needless fur/stripe shimmer.
    roar_mask = feathered_mask(
        neutral_chroma.size,
        [(520, 987, 738, 1142)],
        blur=11,
    )

    subject_matte = neutral_alpha.getchannel("A")
    blink_mask = ImageChops.multiply(blink_mask, subject_matte)
    roar_mask = ImageChops.multiply(roar_mask, subject_matte)

    # Keep even the Gaussian tail away from the lower silhouette.
    lower_taper = Image.new("L", neutral_chroma.size, 0)
    taper = ImageDraw.Draw(lower_taper)
    taper.rectangle((0, 0, neutral_chroma.width, 1150), fill=255)
    for y in range(1151, 1171):
        value = round(255 * (1170 - y) / 19)
        taper.line((0, y, neutral_chroma.width, y), fill=value)
    roar_mask = ImageChops.multiply(roar_mask, lower_taper)

    pairs = (
        ("blink", blink_generated, blink_mask),
        ("roar", roar_generated, roar_mask),
    )
    for state, generated, mask in pairs:
        # Use the already-despilled neutral alpha master as the base so the
        # exterior edge RGB remains identical across all states.
        generated_rgba = generated.convert("RGBA")
        generated_rgba.putalpha(255)
        alpha_out = Image.composite(generated_rgba, neutral_alpha, mask)
        alpha_out.putalpha(subject_matte)
        alpha_out.save(ALPHA / f"{state}-v1.png", optimize=True)
        Image.alpha_composite(exact_green, alpha_out).convert("RGB").save(
            CHROMA / f"{state}-v1.png", optimize=True
        )
        mask.save(AUDIT / f"{state}-localization-mask-v1.png", optimize=True)

        # Fail closed if any output pixel changes where the localization mask
        # is truly zero (the blurred tail is intentionally considered edited).
        delta = ImageChops.difference(alpha_out, neutral_alpha)
        strict_outside = mask.point(lambda value: 255 if value == 0 else 0).convert("RGBA")
        outside = ImageChops.multiply(delta, strict_outside)
        if outside.getbbox() is not None:
            raise RuntimeError(f"{state}: pixels changed outside expression mask")


if __name__ == "__main__":
    main()
