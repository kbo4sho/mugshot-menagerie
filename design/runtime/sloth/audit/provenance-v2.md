# Sleepy Sloth v2 transition-repair provenance

Repair route: one built-in ImageGen mouth-only edit from the accepted v1 neutral, followed by deterministic mouth localization and tongue-color harmonization. No second ImageGen retry was used. Sloth v1 remains intact.

Preserved pixel invariants:

- `design/runtime/sloth/alpha/neutral-v1.png` is the v2 neutral pixel source.
- `design/runtime/sloth/alpha/blink-v1.png` is the v2 blink pixel source.
- All three v2 states use the exact v1 neutral alpha plane.
- Roar edits are clipped to `design/runtime/sloth/audit/roar-localization-mask-v2.png`; everything outside it is neutral pixel-for-pixel.

Generated source:

- Durable raw source: `design/runtime/sloth/audit/generated-roar-v2.png`
- Deterministically harmonized source: `design/runtime/sloth/audit/generated-roar-harmonized-v2.png`
- Original built-in save: `/Users/kevinbolander/.codex/generated_images/01a00c1b-ba37-7c43-9603-0b3c154f1178/exec-a36d220d-df76-4cd8-affc-3a137845e0a8.png`

## Exact targeted prompt

```text
Use case: identity-preserve
Asset type: reactive children's browser game face-mask state, repaired roar target v2
Input images: Image 1 is the sole edit target and must remain pixel-stable outside one compact mouth region.
Primary request: Replace only Image 1's closed smile with one compact, centered, tongue-free delighted O-shaped open mouth engineered to open continuously from the existing smile during a crossfade.
Exact mouth geometry: the new mouth cavity must begin exactly where the current dark smile arc sits, so the cavity's upper rim completely overlaps and absorbs the former smile instead of appearing beneath it. Center the opening under the nose. Make a small vertical rounded O roughly the width of the inner half of the current smile and about 1.25 times as tall as it is wide. Its top edge begins at the current smile's vertical position; its lower edge extends only modestly below. Use one continuous warm dark cocoa mouth interior with a subtle muted coral lower inner-lip glow integrated into the cavity, not a separate tongue. Remove and naturally repaint every pixel of the old smile that falls outside the new O so no horizontal smile line, side hooks, pacifier bar, doubled mouth, or detached lower element remains.
Preserve exactly: same sloth identity; canvas; head silhouette, scale, position, crop, geometry, outer fur and every fur edge; facial disk; muzzle volume and texture outside the compact mouth edit; dark eye-mask patches; open honey-brown eyes; brows; nose; blush; lighting; palette; 2.5D plush-clay finish; exact flat solid #00FF00 background.
Constraints: change only the tight mouth region. No tongue shape, teeth, fangs, gums, drool, uvula, lower detached oval, second mouth, smile crossing the cavity, oversized scream, texture seam, muzzle distortion, head movement, new props, body, text, logo, watermark, shadow, reflection, gradient, or green inside the subject.
Avoid: a mouth emerging below the old smile, pacifier appearance, dangling tongue, open smile, human lips, beak, doubled linework, angry or shocked expression.
```

## Deterministic repair

- The raw ImageGen mouth cavity begins on the v1 smile arc and naturally repaints the obsolete smile.
- A seeded connected-component pass recolors only the eroded, feathered lower cavity interior into one continuous cocoa gradient. The generated rim and cream separation below the nose remain intact; there is no discrete tongue island.
- The mouth-only source is feather-localized onto v1 neutral and receives the exact shared v1 alpha plane.
- Runtime exports are 1024×1024 WebP q95, alpha quality 100, method 6, exact RGB-under-alpha.

## Transition evidence

- `production-roar-weights-380-v2.png` — exact production weights 0, .10, .25, .50, .75, 1.
- `production-roar-weights-96-v2.png` — the same weights at 96px, enlarged 4× nearest-neighbor for inspection.
- `production-roar-ramp-936ms-380-v2.gif` — the production 936ms smoothstep sampled across 24 frames; encoded at the nearest clean GIF duration, 960ms.
- `production-roar-ramp-936ms-96-v2.gif` — matching thumbnail-scale ramp.
- `v1-v2-roar-compare-380.png` — direct critic-gap comparison at .10/.25/.50/.75.
- `manifest-v2.json` — hashes, weight metrics, ramp metrics, alpha/matte parity, and export checks.
