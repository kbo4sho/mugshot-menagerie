# Cuddle Koala v1 provenance

## Built-in generation sources

- Neutral: `/Users/kevinbolander/.codex/generated_images/01a00bef-5381-7ff3-b31e-6d4a80d1ffc7/exec-bb564327-9125-411e-a5eb-e2a9f26235e2.png`
- Blink: `/Users/kevinbolander/.codex/generated_images/01a00bef-5381-7ff3-b31e-6d4a80d1ffc7/exec-543ede5b-4bf0-4dd8-aed8-d74d3d00d8c3.png`
- Roar: `/Users/kevinbolander/.codex/generated_images/01a00bef-5381-7ff3-b31e-6d4a80d1ffc7/exec-f1e7f276-d7d5-44e5-a798-fece1d97f56e.png`

The approved Bumblebee v1 neutral was supplied to the neutral generation only as a style, finish, scale, and composition reference. The koala neutral is a new generation. Blink and roar each used the chosen koala neutral as their sole edit target.

## Exact prompts

### Neutral

```text
Use case: stylized-concept
Asset type: reactive webcam game animal mask, neutral state source master
Input images: Image 1 is a STYLE, FINISH, SCALE, AND COMPOSITION REFERENCE ONLY. It is not an edit target and must not supply the new animal's identity, anatomy, markings, or silhouette.
Primary request: Create one original front-facing chibi Cuddle Koala head on a perfectly flat solid #00FF00 chroma-key field for background removal.
Subject: an unmistakable koala head only: broad rounded blue-silver-gray plush-fur head; two huge fluffy round ears with light cream-gray inner fur; soft crown fluff; one large oval charcoal koala nose; pale rounded lower muzzle; pink cheek blush; giant honey-brown glossy eyes; gentle tiny closed smile with no teeth. No body and no neck.
Style/medium: premium 2.5D plush-clay character render with fine tactile micro-fuzz, softly sculpted volumes, polished animation-film lighting, and the same high quality bar as Image 1 without copying its character.
Composition/framing: perfectly centered and symmetrical, straight-on, head fills about 82% of the square, generous even padding on every side, all ear fur fully inside frame, mask-ready silhouette, no tilt, no perspective distortion.
Lighting/mood: warm cheerful studio key light with subtle dimensional modeling only on the subject; delightful, safe, immediately readable for young children.
Scene/backdrop: one perfectly uniform #00FF00 color with no shadows, gradients, texture, reflections, floor plane, vignette, or lighting variation.
Identity anchor for later state edits: preserve exact head silhouette, position, scale, fur map, palette, highlights, ear shape, crown fluff, nose and muzzle proportions.
Constraints: use no #00FF00 or near-neon green anywhere inside the koala; no background shadow; no cast shadow; no contact shadow; no reflection; no text; no watermark; no props.
Avoid: eucalyptus, leaves, branches, clothing, paws, shoulders, torso, neck, teeth, tongue, open mouth, extra ears, photorealism, flat vector art, muddy gray, scary expression, edge crop.
```

### Blink

```text
Use case: identity-preserve
Asset type: reactive webcam game animal mask, blink state source master
Input images: Image 1 is the sole EDIT TARGET and exact koala identity anchor.
Primary request: Change only the eye expression from open eyes to a fully closed, delighted happy blink: two smooth upward-curving closed eyelids with neat dark lashes, naturally replacing the exact existing eye areas. Keep the tiny closed smile unchanged.
Absolute invariants: preserve pixel-faithfully everywhere outside the smallest necessary eye-and-brow regions. Keep the exact head silhouette, position, scale, crop, ears and every ear-fur strand, crown fluff, forehead and cheek fur maps, blue-silver-gray palette, lighting, highlights, charcoal nose, pale muzzle, pink blush, mouth, background color, and generous padding unchanged. Do not redesign or repaint the character.
Scene/backdrop: retain the exact perfectly uniform solid #00FF00 chroma-key field with no shadows, gradients, texture, floor, or reflections.
Expression: both eyes fully closed in a joyful squint; symmetrical friendly lash arcs; subtle happy cheek lift only if needed; no visible iris or sclera.
Constraints: no #00FF00 inside subject; no teeth; no tongue; no open mouth; no new props; no body; no neck; no text; no watermark.
Avoid: wink, one eye open, sleepy flat lids, scary lashes, shifted geometry, global rerender, changed fur, changed ears, changed nose, changed muzzle, changed blush, changed background.
```

### Roar

```text
Use case: identity-preserve
Asset type: reactive webcam game animal mask, roar state source master
Input images: Image 1 is the sole EDIT TARGET and exact koala identity anchor.
Primary request: Change only the facial expression to delighted playful roaring: replace the tiny closed smile with one compact rounded child-safe O-shaped open mouth centered on the existing muzzle, with a dark warm interior and a small warm coral tongue low inside; add only a subtle lifted-brow expression. Keep both giant honey-brown eyes open and preserve their exact identity. No sharp teeth and preferably no teeth at all.
Absolute invariants: preserve pixel-faithfully everywhere outside the smallest necessary mouth-and-brow regions. Keep the exact head silhouette, position, scale, crop, ears and every ear-fur strand, crown fluff, forehead and cheek fur maps, blue-silver-gray palette, lighting, highlights, charcoal nose, pale muzzle outside the mouth patch, pink blush, eye geometry and reflections, background color, and generous padding unchanged. Do not redesign or repaint the character.
Scene/backdrop: retain the exact perfectly uniform solid #00FF00 chroma-key field with no shadows, gradients, texture, floor, or reflections.
Expression: delighted compact rounded O mouth, dark friendly mouth interior, small warm tongue, subtle lifted brows, excited but sweet and safe.
Constraints: no #00FF00 inside subject; no sharp teeth; no fangs; no giant cavernous mouth; no body; no neck; no props; no text; no watermark.
Avoid: angry roar, scream, fear, aggression, asymmetry, closed eyes, shifted geometry, global rerender, changed fur, changed ears, changed nose, changed muzzle proportions, changed blush, changed background.
```

## Derivation and export

- Chroma removal used the installed `remove_chroma_key.py` helper with border auto-keying, soft matte, thresholds 12/220, and despill.
- Blink pixels were localized to two feathered eye ellipses; roar pixels were localized to the mouth and two brow ellipses. Every pixel outside those zones comes from the neutral master.
- The neutral alpha was imposed on all three localized masters, so silhouette, bbox, alpha centroid, edge coverage, and all 7,169 partially transparent edge pixels are identical across states.
- Runtime exports used `cwebp -q 95 -alpha_q 100 -m 6 -metadata none` at native 1254x1254 resolution.

## QA evidence

- Shared alpha bbox: `(27, 226, 1223, 1041)`.
- Shared alpha centroid: `(625.196, 601.124)`.
- Padding: left 27 px, top 226 px, right 31 px, bottom 213 px.
- All four corner alpha values are zero in all states.
- Nontransparent green-dominant subject pixels: zero in every state.
- Public and GitHub Pages copies are byte-identical; hashes and byte sizes are recorded in `manifest.json`.
- Runtime WebP alpha is present and identical across all three states.
- 380 px WebP-vs-alpha-master parity over both light and dark backgrounds is 52.23-52.56 dB PSNR (0.60-0.62 RGB RMSE).
- Current neutral-to-blink and neutral-to-roar blend was checked at 0/25/50/75/100; alpha remains identical at every step.
- Visual checks: `audit/states-380.png`, `audit/crossfades-380.png`, and `audit/hostile-backgrounds.png`.

## Handoff concern

The character has very wide species-defining ears, leaving 27/31 px side padding (about 2.2/2.5% at native resolution, roughly 8/9 px at the 380 px runtime draw). The silhouette is fully intact and clean, but the independent critic should specifically test edge comfort and live face coverage before approval.
