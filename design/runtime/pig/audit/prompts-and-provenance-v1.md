# Party Pig v1 prompts and provenance

Generation route: built-in Codex ImageGen. Chroma removal used the installed
`remove_chroma_key.py` helper with border auto-key, soft matte, thresholds
12/220, and despill. No CLI image model fallback was used.

## Inputs and generated sources

- Style/composition reference only: `design/runtime/bumblebee/chroma/neutral-v1.png`
- Neutral generated source: `/Users/kevinbolander/.codex/generated_images/01a00c06-f97d-72e2-9348-908a2db42a7e/exec-fdd1909c-2d8a-48b8-91e3-ef6f4034936c.png`
- Blink generated source: `/Users/kevinbolander/.codex/generated_images/01a00c06-f97d-72e2-9348-908a2db42a7e/exec-ea393bdf-b762-47a3-b177-58f6e17b51cd.png`
- Roar generated source: `/Users/kevinbolander/.codex/generated_images/01a00c06-f97d-72e2-9348-908a2db42a7e/exec-d12122cd-b57e-40d2-9a4e-284069ca492c.png`

The expression renders are preserved in `audit/source-blink-v1.png` and
`audit/source-roar-v1.png`. Final states borrow only localized expression
islands, retain neutral-derived pixels everywhere else, and share neutral's
alpha channel exactly.

## Neutral prompt

```text
Use case: stylized-concept
Asset type: reactive webcam game character mask, neutral state master
Input images: Image 1 is style, finish, scale, front-facing composition, padding, lighting, and quality reference only; do not reproduce its species, colors, antennae, wings, stripes, or silhouette.
Scene/backdrop: perfectly flat solid #00FF00 chroma-key field filling the whole square. One exactly uniform color; no gradient, texture, vignette, light variation, floor plane, cast shadow, contact shadow, reflection, or ambient spill.
Subject: an original, unmistakable front-facing chibi rosy-pink pig head only. Broad round cheeks; two floppy triangular pig ears set high and wide; prominent slightly lighter pink oval snout disk centered low on the face with exactly two small dark oval nostrils; tiny crown curl/tuft; soft blush; giant honey-brown glassy eyes. Neutral expression has a tiny gentle closed smile below the snout, mouth closed, no teeth.
Style/medium: premium 2.5D plush-clay character render with refined micro-fuzz and tactile soft sculpting matching Image 1's finish and polish, child-safe and charming.
Composition/framing: square, symmetrical, perfectly front-facing and untilted; head fills roughly 76–80% of canvas width and 72–76% height; centered with generous clean padding on all four sides; no cropped ears or tuft.
Lighting/mood: warm polished studio character lighting on the subject only, cheerful and safe; preserve flat background exactly.
Color palette: rosy pink head, lighter pink muzzle disk, honey-brown eyes, dark brown nostrils and mouth. Never use #00FF00 or chroma green anywhere in the pig.
Constraints: pig head only; no neck, shoulders, body, hooves, mud, farm scene, props, clothing, accessories, labels, text, logos, or watermark. Keep ears unmistakably pig-like rather than round hippo ears. Exactly two nostrils. No open mouth and no teeth. Crisp fully separated silhouette, no green reflections or rim light. Produce one single character, not a sheet or collage.
Avoid: hippo proportions, teddy bear muzzle, extra nostrils, human teeth, tongue, photoreal animal anatomy, flat vector art, floor shadow, green in subject.
```

## Blink prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam game character mask, blink state chroma master
Input images: Image 1 is the sole edit target and identity source.
Primary request: change only the eye and eyebrow expression into a joyful blink. Replace both open eyes with two symmetrical happy closed crescent eyelids with short soft dark lashes; very slightly lift the brow shapes so the expression reads cheerful.
Preserve exactly: the same pig identity, head silhouette, floppy triangular ears, crown curl, rosy palette, oval two-nostril snout, cheeks and blush, tiny closed gentle smile, pose, scale, centered placement, lighting, micro-fuzz texture, and perfectly flat #00FF00 background. Keep the eye regions in the exact same positions and approximate outer footprint as the original open eyes. Everything outside compact eye/brow regions must be pixel-equivalent in visual appearance.
Scene/backdrop: exactly uniform #00FF00 chroma-key field with no gradient, texture, shadow, reflection, or color variation.
Style/medium: premium 2.5D plush-clay, same render and polish as Image 1.
Constraints: pig head only; mouth remains closed; no teeth or tongue; no neck/body/props/text/logo/watermark; no green in subject; no extra elements; do not change camera, crop, geometry, ears, snout, cheeks, facial proportions, or background. Produce one single square image, not a sheet.
```

## Roar prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam game character mask, roar state chroma master
Input images: Image 1 is the sole edit target and identity source.
Primary request: change only the mouth and brow expression into a delighted child-safe roar. Replace the tiny closed smile below the snout with one compact vertical rounded O-shaped open mouth, clearly separated below the oval snout and centered on the face. Mouth interior is warm dark burgundy with a small soft pink tongue visible at the bottom, absolutely no teeth. Very slightly lift both brows for delighted surprise while keeping both giant honey-brown eyes open and unchanged.
Preserve exactly: the same pig identity, head silhouette, floppy triangular ears, crown curl, rosy palette, giant eyes, oval snout disk with exactly two nostrils, cheeks and blush, pose, scale, centered placement, lighting, micro-fuzz texture, and perfectly flat #00FF00 background. Everything outside compact mouth/brow regions must be pixel-equivalent in visual appearance.
Scene/backdrop: exactly uniform #00FF00 chroma-key field with no gradient, texture, shadow, reflection, or color variation.
Style/medium: premium 2.5D plush-clay, same render and polish as Image 1.
Constraints: pig head only; one mouth below the snout; no teeth or fangs; no neck/body/props/text/logo/watermark; no green in subject; no extra elements; do not change camera, crop, geometry, ears, eyes, snout, cheeks, facial proportions, or background. Produce one single square image, not a sheet.
```
