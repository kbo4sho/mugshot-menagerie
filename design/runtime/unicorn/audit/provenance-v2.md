# Twinkle Unicorn v2 matte repair provenance

## Scope

v2 is a deterministic, non-destructive matte repair of v1. No ImageGen call was made. Identity, horn, ears, mane geometry, expression artwork, localized expression masks, mouth normalization, scale, padding, rendering, and WebP settings are inherited from v1. The exact original prompts and generated-source paths remain documented in `prompts-and-provenance-v1.md`.

The independent v1 critic found one blocking issue: the v1 mint repair stopped at raw-source `y=430`, although the mint crown lock curves left and continues below that boundary. At 380 px, partially transparent interior lock pixels exposed a one-to-two-pixel colored seam on hostile backgrounds.

## Repair

- Re-extract the original neutral generated source using the same installed `remove_chroma_key.py` helper, border auto-key, soft matte, 12/220 thresholds, and despill.
- Extend the compact mint-interior source ROI from v1's `[700, 270, 820, 430]` to `[650, 270, 820, 550]`.
- Promote only pixels that were already detected as subject (`alpha > 8`), remained partially transparent (`alpha < 250`), and contain pastel subject material (`red + blue > 220`). This restores 3,349 source pixels from the original generated neutral RGB.
- The extended ROI is wholly inside the head/crown. v2 introduces zero new nonzero-alpha pixels and changes zero alpha pixels outside the inner-crown safety box after scaling.
- Rebuild all three states with the exact shared v2 neutral alpha plane. Expression localization is unchanged from v1.

The deterministic implementation is `export_and_audit_v2.py`; the exact source repair selection is `mint-matte-repair-mask-v2.png`.

## Proof

- Native canonical face/forehead mask: 313,489 of 313,489 pixels have alpha `>= 250`; ratio `1.0`; minimum alpha `255`.
- Actual decoded WebP resized to 380 px: 28,980 of 28,980 canonical pixels have alpha `>= 250`; ratio `1.0`; minimum alpha `255`.
- v1→v2 native alpha changes: 2,200 pixels, bbox `[661, 420, 778, 541]`; all changes are inside the inner-crown safety box.
- New nonzero-alpha pixels: zero. Outer silhouette, bbox, padding, and transparent corners are unchanged.
- Shared v2 alpha bbox: `[125, 91, 1138, 1149]`; padding left/top/right/bottom: `125 / 91 / 116 / 105 px`.
- Visible enclosed holes at alpha threshold 32: zero.
- The 691 conservative green-dominant partial-alpha flags remain on outer antialiasing, not the face: 642 (`92.91%`) have alpha `<= 64`, maximum alpha is `141`, and zero occur inside the canonical face/forehead mask.
- Public and GitHub Pages copies are byte-identical and decode with the exact shared master alpha.
- q95 runtime sizes: neutral 287,632 B; blink 273,758 B; roar 284,844 B.

## Evidence

- `mint-lock-v1-v2-hostile-closeups-380.png`: v1 in the left column and v2 in the right column across dark, green, magenta, cyan, and checker backgrounds. The v1 colored seam is absent in v2.
- `canonical-face-alpha-proof-380-v2.png`: v1 alpha, v2 alpha, and the all-white canonical v2 pass mask.
- `hostile-380-states-v2.png`: all three v2 states on light, dark, green, magenta, cyan, and checker backgrounds.
- `states-380-and-96-v2.png`: actual decoded runtime states at both requested scales.
- `copy-lighter-crossfades-380-v2.png`: neutral→blink and neutral→roar weighted transition evidence.
- `manifest-v2.json`: hashes, parity, alpha topology, canonical-opacity metrics, green-flag distribution, and export sizes.

## Preserved v1 runtime hashes

- neutral: `575287f9dc088e67c5cf78bb95806fd72461de092d537466e15b6bef5c764736`
- blink: `0673de4615f120bd68ede9642c2d4e76f6b5523b70da5a413aca14ad462cc050`
- roar: `2b5f2ef926277361114087a82c817bec03d7101160bc3160b87917e1bd8a56aa`
