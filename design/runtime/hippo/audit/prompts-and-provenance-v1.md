# Happy Hippo v1 — prompts and provenance

## Generation route

- Built-in Codex ImageGen was used for the neutral anchor and both expression edits.
- The approved Bumblebee neutral was used only as the style, finish, and composition reference for neutral generation: `design/runtime/bumblebee/chroma/neutral-v1.png`.
- The selected Hippo neutral was the sole edit target for blink and roar.
- Generated originals remain under `/Users/kevinbolander/.codex/generated_images/01a00bf0-cc59-73e2-ac25-1955f3333108/`.
- Durable copies of all three generated originals are under `design/runtime/hippo/audit/imagegen/`.

## ImageGen sources

- Neutral: `/Users/kevinbolander/.codex/generated_images/01a00bf0-cc59-73e2-ac25-1955f3333108/exec-4641c10f-442f-4a2e-b37e-810b0d8d132e.png`
- Blink: `/Users/kevinbolander/.codex/generated_images/01a00bf0-cc59-73e2-ac25-1955f3333108/exec-b5733127-3932-41bd-ae2b-a5a3509eddc7.png`
- Roar: `/Users/kevinbolander/.codex/generated_images/01a00bf0-cc59-73e2-ac25-1955f3333108/exec-2c672e1b-c8e3-4439-a67c-b17c497161a2.png`

## Neutral prompt

```text
Use case: stylized-concept
Asset type: reactive browser game face-mask character, neutral anchor state
Input images: Image 1 is a STYLE / FINISH / COMPOSITION reference only; do not edit it and do not copy its bee anatomy or colors.
Primary request: Create an original Happy Hippo chibi head with the same premium kid-friendly quality bar as Image 1.
Scene/backdrop: perfectly flat, solid, uniform #00FF00 chroma-key field filling the entire square; absolutely no gradients, texture, vignette, floor plane, lighting variation, reflections, cast shadow, or contact shadow.
Subject: unmistakable broad lavender-gray hippopotamus head only. Tiny high-set round hippo ears with warm pink interiors. A wide squared forward muzzle with one unified lighter lilac-gray muzzle plane/pad—avoid two teddy-bear cheek lobes. Two small nostrils set high on that muzzle. Gentle shallow crown folds. Soft coral blush. Giant honey-brown glossy eyes with large bright catchlights. Neutral expression is a tiny closed gentle smile; mouth fully closed; no visible teeth or tusks.
Style/medium: premium 2.5D chibi plush-clay character render with extremely subtle even micro-fuzz, rounded sculpted volumes, soft studio illumination on the subject, crisp readable silhouette, rich but gentle material detail. Match Image 1's visual sophistication, eye scale, friendly proportions, and polished finish without copying its design.
Composition/framing: centered symmetrical front view, head fills roughly 78–82% of canvas width and 72–78% height, generous uniform padding, entire ears and silhouette visible, no cropping. Keep the face vertically centered for a webcam mask.
Color palette: lavender-gray head, lighter lilac-gray muzzle, honey-brown irises, warm pink inner ears, soft coral blush. Do not use #00FF00 or green anywhere in the subject.
Constraints: one character only; exact head-only cutout candidate; no neck, shoulders, body, water, props, scenery, floor, shadow, text, logo, or watermark. Hippo—not bear, pig, cow, dog, or mouse. Maintain a compact face-mask-friendly silhouette. No teeth, tusks, open mouth, fangs, tongue, or scary expression in this neutral state.
Avoid: teddy-bear muzzle lobes, plush toy seams, eyelashes in neutral, exaggerated snout length, wet realism, pores, wrinkles, chroma spill inside the subject, asymmetry, cropped ears.
```

## Blink prompt

```text
Use case: precise-object-edit
Asset type: reactive browser game face-mask character, blink state
Input images: Image 1 is the sole EDIT TARGET and identity anchor.
Primary request: Change only the eye expression of this exact Happy Hippo to a fully closed joyful blink.
Edit details: replace both open eyes with symmetrical soft downward-curving closed eyelids and a few tiny child-safe happy lashes at the outer corners; let the cheeks read microscopically lifted by the smile. Keep the same tiny closed gentle mouth, nostrils, muzzle, ears, blush, crown folds, head pose, silhouette, padding, colors, lighting, material, micro-fuzz, scale, and exact square composition.
Scene/backdrop: preserve the perfectly flat solid uniform #00FF00 chroma-key background exactly, with no shadows, gradients, texture, floor, reflection, or lighting variation.
Style/medium: preserve the premium 2.5D plush-clay finish and all source texture.
Constraints: edit only the eye/eyelid region; preserve every other pixel-like visual feature as closely as possible; fully closed eyes, no visible iris or sclera; no open mouth, teeth, tusks, tongue, fangs, neck, body, props, text, logo, or watermark. Do not crop or reposition the head. Do not introduce #00FF00 inside the subject.
Avoid: sleepy sadness, wink, asymmetrical eyes, thick makeup lashes, texture drift, color drift, altered muzzle, altered silhouette, extra wrinkles.
```

## Roar prompt

```text
Use case: precise-object-edit
Asset type: reactive browser game face-mask character, joyful roar state
Input images: Image 1 is the sole EDIT TARGET and identity anchor.
Primary request: Change only the expression of this exact Happy Hippo to a joyful compact roar / surprised little “O”.
Edit details: replace the tiny closed smile with one compact vertically rounded open O mouth centered low on the existing muzzle, with a dark warm mouth interior, a small soft pink tongue visible at the bottom, and exactly two very small rounded ivory lower hippo tusk nubs rising subtly from the lower corners—at most two, blunt and friendly, never fangs. Lift the existing brows subtly above the same giant open honey-brown eyes. Keep the eyes, nostrils, wide squared muzzle, ears, blush, crown folds, head pose, silhouette, padding, colors, lighting, material, micro-fuzz, scale, and exact square composition otherwise unchanged.
Scene/backdrop: preserve the perfectly flat solid uniform #00FF00 chroma-key background exactly, with no shadows, gradients, texture, floor, reflection, or lighting variation.
Style/medium: preserve the premium 2.5D plush-clay finish and all source texture.
Constraints: edit only the mouth and immediate brow expression regions; preserve every other pixel-like visual feature as closely as possible; joyful, compact, child-safe mouth; exactly two small rounded LOWER tusk nubs maximum, no upper tusks; no fangs, scary teeth, huge gape, neck, body, water, props, text, logo, or watermark. Do not crop or reposition the head. Do not introduce #00FF00 inside the subject.
Avoid: roaring predator, beaver teeth, buck teeth, multiple teeth, upper canines, teddy-bear muzzle lobes, texture drift, color drift, altered head geometry, altered nostrils, asymmetry.
```

## Deterministic finishing

- `build_localized_states.py` composites only the blink eye islands and the roar brow/mouth islands onto the exact neutral anchor.
- The neutral alpha matte is locked across all three alpha masters and WebP exports.
- The finished chroma PNGs are deterministically flattened over exact `#00FF00`; every fully transparent source-matte pixel is exactly RGB `(0, 255, 0)`.
- `export_and_audit.py` emits q94 / alpha-quality-100 WebPs and identical GitHub Pages copies, plus 380 px hostile-background and copy-plus-lighter crossfade proofs.
