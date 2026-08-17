# Rumble Rhino v2 — clearance repair provenance

## Critic gap

Rhino v1's full-roar cavity left 21 native centerline pixels below the mouth, which reduced to six clear rows at 380 px and one at 96 px. Under ±7° rotation on light and black, the cavity visually merged with the lower silhouette.

## Route

- No new ImageGen call or prompt was used for v2.
- This is a deterministic source-preservation repair built from the approved v1 alpha masters.
- Source masters:
  - `design/runtime/rhino/alpha/neutral-v1.png`
  - `design/runtime/rhino/alpha/blink-v1.png`
  - `design/runtime/rhino/alpha/roar-mid-v1.png`
  - `design/runtime/rhino/alpha/roar-v1.png`
- Build script: `design/runtime/rhino/audit/build_v2_clearance_repair.py`

## Repair

Only the full-roar lower cavity boundary changes. A rounded, feathered mask raises the lower edge while leaving the upper rim intact. Pixels removed from the lower cavity are replaced with canonical neutral-state pixels from the same muzzle/chin coordinates, preserving continuous lavender material and texture without synthesized paint or a hard seam.

- Changed full-roar RGB pixels: 9,258.
- Changed bbox: `[524, 1050, 730, 1120]`.
- Maximum RGB delta outside the repair ROI: 0.
- Neutral v1→v2 maximum pixel delta: 0.
- Blink v1→v2 maximum pixel delta: 0.
- Roar-mid v1→v2 maximum pixel delta: 0.
- Alpha is byte-identical across all four v2 states and unchanged from v1.

## Exact clearance result

“Clearly lavender opaque” means alpha ≥240/255, mean RGB luminance ≥80, and blue no more than four levels below green along the rotated cavity-center probe.

| Output | −7° | 0° | +7° |
| --- | ---: | ---: | ---: |
| 96 px, light | 3 | 4 | 3 |
| 96 px, black | 3 | 4 | 3 |
| 380 px, light | 16 | 16 | 16 |
| 380 px, black | 16 | 16 | 16 |

At every helper weight from 0 through 1 in 0.125 increments, the mouth ROI has exactly one connected dark semantic component at the recorded threshold; no secondary smile component appears.

## Export

- Alpha and chroma masters: 1254 × 1254 PNG.
- Runtime: 1254 × 1254 WebP, quality 95, alpha quality 100, method 6, exact alpha.
- Runtime sizes: neutral 288,938 bytes; blink 285,804; roar-mid 280,082; roar 281,424.
- Public and GitHub Pages copies are byte-identical.
- v1 files remain preserved alongside v2.

Full hashes, per-angle probes, helper connectivity, state metrics, and evidence paths are recorded in `design/runtime/rhino/audit/manifest-v2.json`.
