from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
PIG = ROOT / "design" / "runtime" / "pig"
CHROMA = PIG / "chroma"
ALPHA = PIG / "alpha"
AUDIT = PIG / "audit"


def localized_difference_mask(
    neutral: Image.Image,
    variant: Image.Image,
    regions: list[tuple[str, tuple[int, int, int, int]]],
    threshold: int = 18,
    expand: int = 29,
    blur: int = 11,
) -> Image.Image:
    neutral_array = np.asarray(neutral, dtype=np.int16)
    variant_array = np.asarray(variant, dtype=np.int16)
    difference = np.max(np.abs(variant_array - neutral_array), axis=2)
    changed = Image.fromarray(np.where(difference >= threshold, 255, 0).astype(np.uint8))

    region_mask = Image.new("L", neutral.size, 0)
    draw = ImageDraw.Draw(region_mask)
    for kind, box in regions:
        if kind == "ellipse":
            draw.ellipse(box, fill=255)
        else:
            draw.rounded_rectangle(box, radius=40, fill=255)
    changed = ImageChops.multiply(changed, region_mask)
    changed = changed.filter(ImageFilter.MaxFilter(expand))
    changed = ImageChops.multiply(changed, region_mask)
    return changed.filter(ImageFilter.GaussianBlur(blur))


def main() -> None:
    neutral = Image.open(CHROMA / "neutral-v1.png").convert("RGB")
    blink_source = Image.open(AUDIT / "source-blink-v1.png").convert("RGB")
    roar_source = Image.open(AUDIT / "source-roar-v1.png").convert("RGB")

    # Diff-gated eye islands remove the generated open eyes completely, but do
    # not carry regenerated cheek, snout, ear, silhouette, or background pixels.
    blink_mask = localized_difference_mask(
        neutral,
        blink_source,
        [
            ("ellipse", (220, 470, 555, 870)),
            ("ellipse", (695, 470, 1030, 870)),
        ],
    )

    # The roar state borrows only the two lifted brows and compact O mouth. The
    # giant eyes and every perimeter pixel remain exactly neutral-derived.
    roar_mask = localized_difference_mask(
        neutral,
        roar_source,
        [
            ("rounded", (275, 410, 510, 570)),
            ("rounded", (750, 410, 985, 570)),
            ("ellipse", (515, 875, 735, 1082)),
        ],
        threshold=16,
        expand=31,
        blur=12,
    )

    subject_matte = Image.open(ALPHA / "neutral-v1.png").convert("RGBA").getchannel("A")
    blink_mask = ImageChops.multiply(blink_mask, subject_matte)
    roar_mask = ImageChops.multiply(roar_mask, subject_matte)

    # Keep the O-mouth blend well clear of the bottom antialiased silhouette.
    lower_taper = Image.new("L", neutral.size, 255)
    taper_draw = ImageDraw.Draw(lower_taper)
    for y in range(1070, 1096):
        value = round(255 * (1095 - y) / 25)
        taper_draw.line((0, y, neutral.width, y), fill=value)
    taper_draw.rectangle((0, 1096, neutral.width, neutral.height), fill=0)
    roar_mask = ImageChops.multiply(roar_mask, lower_taper)

    Image.composite(blink_source, neutral, blink_mask).save(CHROMA / "blink-v1.png")
    Image.composite(roar_source, neutral, roar_mask).save(CHROMA / "roar-v1.png")
    blink_mask.save(AUDIT / "blink-localization-mask-v1.png")
    roar_mask.save(AUDIT / "roar-localization-mask-v1.png")

    # Every truly unmasked pixel must be bit-identical to the neutral master.
    for state, mask in (("blink", blink_mask), ("roar", roar_mask)):
        output = Image.open(CHROMA / f"{state}-v1.png").convert("RGB")
        delta = ImageChops.difference(output, neutral)
        strict_outside = mask.point(lambda value: 255 if value == 0 else 0).convert("RGB")
        outside = ImageChops.multiply(delta, strict_outside)
        if outside.getbbox() is not None:
            raise RuntimeError(f"{state}: pixels changed outside localized expression mask")


if __name__ == "__main__":
    main()
