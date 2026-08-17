from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
HIPPO = ROOT / "design" / "runtime" / "hippo"
CHROMA = HIPPO / "chroma"
AUDIT = HIPPO / "audit"
SOURCES = AUDIT / "imagegen"


def feathered_mask(size: tuple[int, int], shapes: list[tuple[str, tuple[int, int, int, int], int]], blur: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for kind, box, radius in shapes:
        if kind == "ellipse":
            draw.ellipse(box, fill=255)
        else:
            draw.rounded_rectangle(box, radius=radius, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def main() -> None:
    neutral = Image.open(SOURCES / "neutral-v1.generated.png").convert("RGB")
    blink_generated = Image.open(SOURCES / "blink-v1.generated.png").convert("RGB")
    roar_generated = Image.open(SOURCES / "roar-v1.generated.png").convert("RGB")

    # The two eye islands fully cover the neutral eyeballs while fading back into
    # the exact neutral forehead and muzzle. All exterior geometry stays locked.
    blink_mask = feathered_mask(
        neutral.size,
        [
            ("ellipse", (235, 455, 585, 765), 0),
            ("ellipse", (670, 455, 1020, 765), 0),
        ],
        blur=14,
    )

    # Roar borrows only the lifted brows and compact O-mouth. The eyes, nostrils,
    # cheek planes, ears, silhouette, lighting, and micro-fuzz remain neutral.
    roar_mask = feathered_mask(
        neutral.size,
        [
            ("rounded", (300, 265, 535, 390), 52),
            ("rounded", (720, 265, 955, 390), 52),
            ("ellipse", (505, 870, 750, 1135), 0),
        ],
        blur=15,
    )
    neutral_alpha_path = HIPPO / "alpha" / "neutral-v1.png"
    if neutral_alpha_path.exists():
        neutral_subject_matte = Image.open(neutral_alpha_path).convert("RGBA").getchannel("A")
        blink_mask = ImageChops.multiply(blink_mask, neutral_subject_matte)
        roar_mask = ImageChops.multiply(roar_mask, neutral_subject_matte)
    # Keep the mouth edit away from the lower silhouette so even RGB texture at
    # the perimeter is neutral-identical during copy + lighter crossfades.
    lower_taper = Image.new("L", neutral.size, 0)
    taper_draw = ImageDraw.Draw(lower_taper)
    taper_draw.rectangle((0, 0, neutral.width, 1095), fill=255)
    for y in range(1096, 1123):
        value = round(255 * (1122 - y) / (1122 - 1095))
        taper_draw.line((0, y, neutral.width, y), fill=value)
    roar_mask = ImageChops.multiply(roar_mask, lower_taper)

    Image.composite(blink_generated, neutral, blink_mask).save(CHROMA / "blink-v1.png")
    Image.composite(roar_generated, neutral, roar_mask).save(CHROMA / "roar-v1.png")
    blink_mask.save(AUDIT / "blink-localization-mask-v1.png")
    roar_mask.save(AUDIT / "roar-localization-mask-v1.png")

    # Guard the source-preservation contract: every pixel outside the edit masks
    # must be exactly identical to neutral.
    for state, mask in (("blink", blink_mask), ("roar", roar_mask)):
        output = Image.open(CHROMA / f"{state}-v1.png").convert("RGB")
        delta = ImageChops.difference(output, neutral)
        # Gaussian blur has a long low-value tail. Pixels where the stored mask
        # is exactly zero are the true invariant exterior.
        strict_outside = mask.point(lambda value: 255 if value == 0 else 0).convert("RGB")
        outside = ImageChops.multiply(delta, strict_outside)
        if outside.getbbox() is not None:
            raise RuntimeError(f"{state}: pixels changed outside localized expression mask")


if __name__ == "__main__":
    main()
