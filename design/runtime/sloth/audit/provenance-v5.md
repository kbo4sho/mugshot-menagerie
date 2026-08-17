# Sleepy Sloth v5 four-state bridge provenance

## Production route

- Architecture: optional `roarMid` bridge implemented by `app/rendered-mask-blend.mjs`.
- Blend-helper SHA-256: `40cf3b04a71f660652cd2a7d5ce835ae22f89488352189c2301d4dc25785ec47`.
- Accepted sources: `design/runtime/sloth/alpha/neutral-v1.png` and `design/runtime/sloth/alpha/blink-v1.png`.
- Generation method: deterministic localized RGB construction from accepted neutral v1. ImageGen was not used, so v5 has no generation prompt.
- v1-v4 remain preserved.

## Authored bridge

- `roar-mid-v5` is a shallow cocoa opening whose upper rim is sampled from the accepted central smile.
- `roar-v5` uses the exact same authored upper rim and tonal source, then expands downward to a compact child-safe yawn opening.
- Native shared upper-rim span: `x=574..680`, `y=842.333..852.778`.
- Mid center depth: 43 native pixels; roar center depth: 112 native pixels.
- Original smile segments outside the shared rim are repainted with sampled cream muzzle texture.
- Both edits are localized to native `x=515..724, y=815..969`; maximum RGB delta outside that ROI is zero.

## Exact helper-driven weights

The proof script invokes the production helper with blink weight zero and `hasRoarMid=true`.

| Jaw | Neutral | Roar mid | Roar |
| ---: | ---: | ---: | ---: |
| 0.00 | 1.00 | 0.00 | 0.00 |
| 0.10 | 0.80 | 0.20 | 0.00 |
| 0.25 | 0.50 | 0.50 | 0.00 |
| 0.50 | 0.00 | 1.00 | 0.00 |
| 0.75 | 0.00 | 0.50 | 0.50 |
| 1.00 | 0.00 | 0.00 | 1.00 |

The 96 px proof downsamples the exact production 380 px composite; it does not remix resized sources.

## Outputs

- Native alpha masters: `design/runtime/sloth/alpha/{neutral,blink,roar-mid,roar}-v5.png`
- Native chroma masters: `design/runtime/sloth/chroma/{neutral,blink,roar-mid,roar}-v5.png`
- Runtime assets: `public/masks/sloth/{neutral,blink,roar-mid,roar}-v5.webp`
- GitHub Pages copies: `github-pages/public/masks/sloth/{neutral,blink,roar-mid,roar}-v5.webp`

Runtime encoding is 1024 px WebP at quality 95, alpha quality 100, method 6. Sizes are 304,994 bytes neutral; 302,412 blink; 303,880 roar-mid; and 302,662 roar. Public and Pages hashes match state by state.

## Preservation and audit

- Neutral v5 is byte-identical to neutral v1.
- Blink v5 is byte-identical to blink v1.
- Native and decoded-runtime alpha hashes are identical across all four states.
- Chroma corners are exact `#00FF00` in all four masters.
- Runtime alpha bbox is `[62, 122, 961, 905]`, padding is `[62, 122, 63, 119]`, and centroid is `[510.362, 532.116]` for every state.
- Cream separation between nose and mouth is nine compositor rows at jaw 0 and 0.10, then seven rows at jaw 0.25 through 1.00.
- At jaw 0 through 0.50, luminance thresholds 75 through 150 each find one significant mouth component in the mouth-only crop. At jaw 1.00, thresholds 75 through 165 each find one.
- At jaw 0.75, threshold 105 isolates the dark authored top from the lighter in-progress lower expansion; thresholds 120 through 165 find one connected component. The 380 px and 96 px visual proofs show the lighter region touching the authored top without a muzzle gap. This remains the specific item for independent critic judgment.
- The inherited v1 matte reports 138 green-dominant partial-alpha pixels at runtime; v5 is identical to v1 on this metric and hostile-background review shows no new edge change.

## Review status

Awaiting independent critic review. This asset pack is not self-approved and has not been added to the app registry or asset ledger.
