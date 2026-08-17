# Party Parrot v3 repair record

Critic gap: Party Parrot v2 removed the pale side-wrapping horseshoe and fixed the doubled-beak transition, but left a detached dark crescent below the compact charcoal point. The crescent read as a second dark dash at native size and at intermediate roar weights.

## Source preservation

- Sole visual source: `design/runtime/parrot/alpha/roar-v2.png`.
- `neutral-v3.png` and `blink-v3.png` are byte/pixel-identical copies of their v2 counterparts, which are themselves identical to v1.
- v1 and v2 alpha, chroma, runtime, and Pages assets remain present and unchanged.
- No ImageGen generation or edit was used for v3.

## Selected deterministic repair

1. Inside the detached-crescent polygon only, sample scarlet feather pixels from the same lower-feather rows at symmetric horizontal offsets of 90px. Cross-blend those real texture samples left-to-right and composite them through a 5px soft mask. This removes the crescent without a flat fill, dark dash, or hard clone seam.
2. Reuse the exact existing v2 lower-horn pixels from `(594, 929, 662, 970)`, stretch them laterally from 68px to 80px, and composite through a compact 1.6px-soft rounded polygon. The attached lower mandible's dark core broadens from 47px to 54px while retaining the same material, lighting, vertical placement, and direct join to the burgundy cavity.
3. Reapply the exact v2 shared alpha mask. No silhouette, feather map, upper beak, cavity, eye, brow, crown, or cheek pixel outside the union repair mask changes.

Repair masks:

- `design/runtime/parrot/v3-audit/roar-detached-crescent-replacement-mask-v3.png`
- `design/runtime/parrot/v3-audit/roar-lower-mandible-reshape-mask-v3.png`
- `design/runtime/parrot/v3-audit/roar-final-localization-mask-v3.png`

## Export

- Alpha masters: 1254×1254 PNG.
- Chroma masters: exact flat `#00FF00` outside the shared alpha.
- Runtime: 1344×1344 WebP, q95, alpha q100, method 6, exact mode.
- Public and GitHub Pages copies are byte-identical.

## Evidence

- `design/runtime/parrot/v3-audit/native-states-v3.jpg`
- `design/runtime/parrot/v3-audit/native-96-380-states-v3.png`
- `design/runtime/parrot/v3-audit/hostile-380-states-v3.png`
- `design/runtime/parrot/v3-audit/roar-transition-96-v3.png`
- `design/runtime/parrot/v3-audit/roar-transition-380-v3.png`
- `design/runtime/parrot/v3-audit/v2-v3-roar-comparison-380.png`
- `design/runtime/parrot/v3-audit/manifest-v3.json`

This record documents production and validation only; it does not self-approve the asset.
