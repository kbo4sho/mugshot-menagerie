# Rumble Rhino v1 — prompts and provenance

## Route and image roles

- Generation route: built-in ImageGen.
- `design/runtime/bumblebee/chroma/neutral-v1.png`: finish, composition, scale, camera, and chibi-quality reference only for the new neutral. It was not an edit target.
- `design/runtime/rhino/audit/generated-neutral-v1.png`: sole edit target for every authored expression state.
- Final generated sources:
  - `design/runtime/rhino/audit/generated-neutral-v1.png`
  - `design/runtime/rhino/audit/generated-blink-v1.png`
  - `design/runtime/rhino/audit/generated-roar-mid-v1.png`
  - `design/runtime/rhino/audit/generated-roar-v1.png`
- Rejected iteration receipts are retained as `generated-roar-mid-oval-rejected-v1.png` and `generated-roar-high-rejected-v1.png`.
- Local deterministic work is limited to chroma removal, safe expression localization, shared-alpha locking, a compact vertical registration of pixels from the neutral-targeted full-roar source, WebP encoding, and audit rendering.

## Neutral prompt

```text
Use case: stylized-concept
Asset type: reactive webcam game animal face mask, neutral canonical state
Input images: Image 1 is a finish, rendering, scale, camera, composition, and chibi quality reference only; do not retain the bee’s anatomy, palette, antennae, wings, or stripes.
Primary request: Create an unmistakable front-facing chibi rhinoceros head for the kid-safe Giggle Zoo game.
Scene/backdrop: exactly one perfectly flat, uniform solid #00FF00 chroma-key field filling every pixel outside the subject. No gradients, shadows, texture, lighting variation, floor, horizon, reflection, or vignette.
Subject: only a slate-gray with faint lavender undertone rhinoceros head, centered and symmetrical. Broad armored rhino skull and broad squared muzzle. One large centered rounded ivory-gray horn emerging from the snout and a distinctly much smaller second horn directly behind it on the forehead. Two small rounded ears high at the sides. Heavy but cute brow folds, two clear nostrils, subtle rhino armor-skin folds and fine plush-clay microtexture, soft peach-lilac blush, giant warm honey-brown glossy eyes. Neutral expression with a tiny gentle closed smile and absolutely no visible teeth.
Style/medium: premium 2.5D plush-clay character render matching Image 1’s tactile softness, warm polished lighting, crisp silhouette, expressive oversized eyes, and toy-like dimensional finish; original animal design.
Composition/framing: straight-on orthographic-feeling close-up, entire head only with no neck or body. Face and muzzle occupy most of the square while keeping generous safe padding above the tall main horn and around both ears; no cropping or tangent to canvas. Canonical face-coverage silhouette suitable for overlaying a child’s entire face. Keep both eyes at the same height and mouth centered on the vertical axis.
Lighting/mood: bright friendly studio illumination on the subject only; adorable, warm, playful, safe.
Color palette: slate and lavender-gray skin, slightly lighter broad muzzle, warm honey-brown irises, muted peach-lilac cheeks, ivory-gray horns. Do not use #00FF00 or green anywhere in the subject.
Materials/textures: opaque plush-clay rhino skin with subtle folds and microtexture; not glossy plastic, not realistic hide.
Constraints: no body, no neck, no legs, no savanna, no grass, no scenery, no props, no labels, no text, no watermark, no cast/contact shadow, no transparent or translucent subject regions. Exactly two horns: one large central snout horn and one much smaller horn immediately behind it. Preserve an opaque solid face plate behind the eyes and mouth for webcam coverage.
Avoid: hippopotamus anatomy, horse anatomy, elephant trunk, tusks, long ears, side profile, angry expression, sharp horn, extra horns, asymmetric crop, floor plane, subject-colored green spill.
```

## Blink prompt

```text
Use case: identity-preserve
Asset type: reactive webcam game animal face mask, bilateral blink state
Input images: Image 1 is the sole edit target and canonical Rhino neutral state.
Primary request: Change only the expression into a joyful bilateral blink. Replace both open glossy eyes with matching closed happy upward-curving plush-clay eyelid arcs. Keep the tiny gentle closed smile exactly calm and toothless.
Constraints: preserve the exact same rhinoceros identity, two horns (one large centered rounded snout horn and one much smaller horn directly behind it), ears, broad squared muzzle, nostrils, head silhouette, scale, crop, position, lighting, slate/lavender-gray palette, blush, material, microtexture, and every non-eye pixel as closely as possible. Both eyes must be closed, symmetric, and at the same height. Preserve the perfectly flat uniform #00FF00 field exactly; do not put green in the subject. No body, neck, props, scenery, shadow, text, watermark, teeth, tongue, open mouth, extra horns, or extra facial features. This must be an expression-only state with no camera, geometry, texture, or background drift.
```

## Final roar-mid prompt

```text
Use case: identity-preserve
Asset type: reactive webcam game animal face mask, corrected authored `roar-mid` transition bridge
Input images: Image 1 is the sole edit target and canonical Rhino neutral state.
Primary request: Change only the mouth into a small shallow open happy mouth whose U-shaped cavity grows directly downward from the neutral smile curve. The neutral smile curve must become the opening’s upper edge, so this is one connected mouth shape—not a smile plus a separate hole. Make a compact dark warm-plum cavity shaped like a short rounded bowl/crescent: broad enough to inherit the neutral smile’s central width, shallow vertically, centered exactly on the same vertical axis. No separate black line across the cavity, no second opening, and no smile remnants beside it. Keep both giant honey-brown eyes open; lift the existing brows only very slightly.
Constraints: this is the halfway bridge from closed smile to the full vertical O roar. Preserve the exact rhinoceros identity, two horns, eyes, ears, broad squared muzzle, nostrils, head silhouette, scale, crop, position, lighting, slate/lavender-gray palette, blush, material, microtexture, and every non-mouth/non-brow pixel as closely as possible. Exactly one mouth cavity, uniform interior, with absolutely no teeth, tongue, gums, uvula, split cavity, inner highlights, or side remnants. Preserve the perfectly flat uniform #00FF00 field exactly; no green in the subject. No body, neck, props, scenery, shadow, text, watermark, extra horns, tusks, or extra features. No camera, geometry, texture, or background drift.
```

## Final full-roar prompt

```text
Use case: identity-preserve
Asset type: reactive webcam game animal face mask, corrected full roar state
Input images: Image 1 is the sole edit target and canonical Rhino neutral state.
Primary request: Change only the mouth into one compact child-safe surprised O that grows downward from the neutral smile’s exact position. The O’s top boundary must begin on the same curved line and at the same vertical level as the neutral smile, then extend downward into a short vertical rounded oval. Fully remove the neutral smile line: it becomes the upper rim of the opening and must not cross the cavity. Use a single uniform deep warm-plum/dark-brown cavity with a soft plush-clay rim. Keep both giant honey-brown eyes open and lift the existing brows into a delighted surprised expression.
Constraints: preserve the exact rhinoceros identity, two horns, eyes, ears, broad squared muzzle, nostrils, head silhouette, scale, crop, position, lighting, slate/lavender-gray palette, blush, material, microtexture, and all pixels outside the brow and compact mouth zones as closely as possible. The full O must be larger and deeper than the shallow roar-mid bowl but still compact, vertically rounded, centered on the axis, entirely inside the muzzle, and separated from the bottom silhouette by comfortable visible chin padding. Exactly one cavity; absolutely no smile line across it, no second opening, teeth, tongue, gums, uvula, split cavity, inner shapes, highlights, or side remnants. Preserve the perfectly flat uniform #00FF00 field exactly; no green in the subject. No body, neck, props, scenery, shadow, text, watermark, extra horns, tusks, or extra features. No camera, geometry, texture, or background drift.
```

## Deterministic export

- Script: `design/runtime/rhino/audit/build_export_audit.py`
- Chroma removal: installed ImageGen `remove_chroma_key.py`, border auto-key, soft matte, thresholds 12/220, despill, one-pixel edge contract.
- Canonical alpha: the neutral alpha is applied byte-for-byte to all four masters.
- Runtime export: 1254 × 1254 WebP, quality 95, alpha quality 100, method 6, exact alpha.
- Public and GitHub Pages copies are byte-identical; see `manifest-v1.json` for hashes and measurements.
