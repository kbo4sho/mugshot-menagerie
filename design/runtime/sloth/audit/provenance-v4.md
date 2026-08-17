# Sleepy Sloth v4 provenance and review outcome

## Source and method

- Accepted identity source: `design/runtime/sloth/alpha/neutral-v1.png`
- Accepted blink source: `design/runtime/sloth/alpha/blink-v1.png`
- Roar construction: deterministic local RGB repair from the v1 neutral. No ImageGen call was used for v4.
- New cavity: one near-uniform dark-cocoa ellipse at native coordinates `(574, 858, 680, 958)`.
- Smile erase: sampled cream muzzle texture replaces the target smile side segments before the cavity is composited.
- Alpha: copied exactly from v1 for all three states.
- Local repair boundary: native RGB changes are confined to `x=500..749, y=830..969`; maximum channel delta outside that ROI is `0`.

## Export

- Runtime encoding: 1024 px lossless-alpha WebP, quality 95, alpha quality 100, method 6.
- Public and GitHub Pages copies are byte-identical for each state.
- v4 sizes: neutral 304,994 bytes; blink 302,412 bytes; roar 302,948 bytes.
- v1-v3 remain preserved.

## Verification

- Neutral v4 is byte-identical to neutral v1.
- Blink v4 is byte-identical to blink v1.
- All state alpha-pixel hashes are `dec0097e101680317b56c3da50a1277effb47fd723b30eb66b1c08b243d51a48`.
- The fixed runtime cream strip between nose and mouth measures nine center rows at every audited weight.
- The endpoint cavity is uniform dark cocoa with no tongue, lighter lower lobe, or nose-fused shelf.

## Review outcome: BLOCKED

The authoritative 380 px and 96 px production copy-plus-lighter sheets still show the lower cavity as a perceptually separate oval at early weights, most clearly at 0.25 and still present at 0.50. The luminance audit corroborates this: at weight 0.25, threshold 135 produces two significant components (156 px upper smile and 53 px lower cavity); threshold 150 produces two components (184 px upper smile and 383 px lower cavity). At weight 0.50, threshold 105 produces two significant components (63 px upper smile and 155 px lower cavity).

The DeltaE report's joined-component value is not sufficient evidence of a pass because it deliberately unions the visible target delta with the neutral-smile anchor. That union can bridge the two perceptual forms even when the actual production image still reads as detached.

Per the one-design-iteration limit, v4 is retained as non-destructive evidence but is not recommended for approval or registry integration.
