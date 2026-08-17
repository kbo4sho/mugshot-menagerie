# Bubbly Octopus v1 — prompts and provenance

## Source roles

- `design/runtime/bumblebee/alpha/neutral-v1.png` was used only as the finish, lighting, composition, scale, centering, eye-design, cheek, and child-safe polish reference for the original neutral generation. It was not an edit target.
- `design/runtime/octopus/chroma/neutral-raw-v1.png` was the sole edit target and identity anchor for both expression generations and the single roar retry.
- Built-in ImageGen generated all native source images. The successful generated sources are archived as `audit/{neutral,blink,roar}-generated-v1.png`; the rejected first roar is preserved as `audit/roar-generated-rejected-tongue-v1.png`.
- Local chroma removal used the installed `remove_chroma_key.py` helper with border auto-keying, soft matte, thresholds 12/220, and despill.
- `audit/export_and_audit.py` localizes blink to two feathered eye islands and roar to one feathered compact mouth island plus two brow islands. Every pixel outside those expression regions comes from neutral, and the exact neutral alpha plane is imposed on all three states.
- Final chroma masters are deterministically recomposited over exact `#00FF00`. Runtime WebPs use q95, alpha quality 100, method 6, exact mode, and byte-identical public/Pages copies.

## Neutral generation prompt

```text
Use case: stylized-concept
Asset type: reactive webcam game animal face-mask, neutral-state chroma source
Primary request: Generate one brand-new original front-facing chibi Bubbly Octopus head/face-mask on an exact perfectly flat solid #00FF00 chroma-key field for clean local removal. Image 1 is a finish, lighting, composition, scale, centering, eye-design, cheek, and child-safe polish reference only; do not edit it, copy its anatomy, or include bee features.
Scene/backdrop: one perfectly uniform exact #00FF00 field edge-to-edge, with absolutely no gradient, vignette, texture, floor plane, horizon, water, lighting variation, reflection, shadow, glow, or bubbles.
Subject: exactly one unmistakable octopus face-mask/head, front-facing and symmetrical. A rounded coral-purple mantle/head forms the main face. Arrange six to eight short, chunky curled tentacle tips as a compact attached lower-face ruff, fully contained close to the head silhouette rather than spreading into a body. Add only subtle small suction-cup texture accents on the tucked tentacle tips. Giant glossy honey-brown eyes with warm amber irises and bright catchlights, small coral blush cheeks, and a tiny gentle closed smile with no visible teeth.
Style/medium: premium polished 2.5D plush-clay character render matching the reference's softly sculpted volume, tactile microtexture, clean rounded forms, warm child-safe expression, crisp antialiased silhouette, and refined game-asset finish.
Composition/framing: one centered square head-only mask, straight-on, filling a similar proportion of the square as Image 1; generous clear padding on every side; all mantle and curled tentacle tips fully inside frame; opaque forehead/crown and central face coverage.
Lighting/mood: soft warm frontal studio modeling contained entirely on the subject; joyful, gentle, cozy.
Color palette: coral-purple and raspberry-violet head/tentacles, slightly lighter lavender suction-cup accents, honey-brown/amber eyes, peach-coral blush. Do not use #00FF00 or near-chroma green anywhere in the subject.
Materials/textures: softly matte plush-clay skin with restrained tactile grain; subtle suction-cup detail accents only; no wet, slimy, glassy, translucent, or underwater treatment.
Constraints: exactly one octopus head/face-mask; six to eight short curled attached tentacle tips forming a compact lower ruff; neutral gentle closed smile; zero visible teeth, tongue, or open mouth; giant eyes open; no neck, torso, shoulders, arms extending outward, full-body tentacle spread, squid fins, jellyfish dome, beak, water, seascape, bubbles, coral reef, props, clothing, accessories, text, letters, logos, watermark, floor, cast/contact shadow, reflection, detached pieces, holes in the central face, or chroma spill. The chroma field must remain a single exact flat solid #00FF00 all the way to the clean subject edge.
Avoid: squid silhouette, jellyfish silhouette, starfish, realistic cephalopod, floating tentacles, long trailing arms, asymmetry, muddy eyes, aggressive expression, extra facial features, green details, clipped silhouette.
```

## Blink edit prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face-mask, blink-state chroma source
Primary request: Edit Image 1, the sole target and identity anchor, into the blink expression. Change only the expression: replace both open eyes with two bilateral, matching happy closed-eye arcs, gently curved upward at the outer corners. Preserve the tiny neutral closed smile.
Scene/backdrop: preserve the exact same perfectly flat uniform solid green chroma field, with no shadow, gradient, texture, floor, reflection, water, bubbles, or variation.
Identity invariants: keep the exact same Bubbly Octopus identity, rounded coral-purple mantle/head, proportions, placement, scale, silhouette, six-to-eight compact attached curled tentacle tips, suction-cup accents, blush, plush-clay material, lighting, colors, padding, and all non-eye pixels as visually identical to Image 1 as possible. Do not redesign or move tentacles. Do not change the head contour, texture map, cheeks, mouth, or backdrop.
Transition requirement: this state will be localized to the two eye regions and blended over neutral using premultiplied copy-plus-lighter weights, so there must be no skin or tentacle shimmer outside the eye expression regions.
Expression: both eyes fully closed as thick, smooth, dark chocolate happy arcs; bilateral and symmetrical; no visible iris, pupil, sclera, catchlight, eyelashes, or wink. Keep brows subtle and relaxed. Mouth remains the same tiny gentle closed smile with no opening, tongue, or teeth.
Constraints: change only both eyes; no wink; no added props, text, logos, watermark, body, water, bubbles, squid fins, jellyfish cues, detached pieces, green subject detail, shadow, floor, reflection, or new elements. Keep every part fully within frame and the background one removable flat field.
```

## First roar edit prompt (rejected for visible tongue)

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face-mask, joyful roar-state chroma source
Primary request: Edit Image 1, the sole target and identity anchor, into a joyful compact roar expression. Change only the mouth and subtle brow expression: replace the tiny closed smile with one small-to-medium centered rounded O mouth, and gently lift both brows. Keep both giant honey-brown eyes open and preserve their exact identity.
Scene/backdrop: preserve the exact same perfectly flat uniform solid green chroma field, with no shadow, gradient, texture, floor, reflection, water, bubbles, or variation.
Identity invariants: keep the exact same Bubbly Octopus identity, rounded coral-purple mantle/head, proportions, placement, scale, silhouette, six-to-eight compact attached curled tentacle tips, suction-cup accents, blush, eyes, plush-clay material, lighting, colors, padding, and all non-expression pixels as visually identical to Image 1 as possible. Do not redesign or move tentacles. Do not change the head contour, skin texture map, cheeks, eye geometry, or backdrop.
Transition requirement: this state will be localized to the compact mouth and two small brow regions and blended over neutral using premultiplied copy-plus-lighter weights, so there must be no skin or tentacle shimmer outside those expression regions.
Expression: one compact joyful centered rounded O-shaped open mouth with a uniform warm deep-plum interior; no tongue, no teeth, no gums, no beak, and no split or double mouth. Mouth stays well above the tentacle ruff and substantially narrower than the distance between the inner eye corners. Both brows lift subtly and symmetrically; eyes remain bright, open, friendly, and unchanged.
Constraints: change only mouth and subtle brows; no wide jaw, no grin, no tongue, teeth, fangs, beak, drool, or aggressive snarl; no added props, text, logos, watermark, body, water, bubbles, squid fins, jellyfish cues, detached pieces, green subject detail, shadow, floor, reflection, or new elements. Keep every part fully within frame and the background one removable flat field.
```

## Targeted roar retry prompt (accepted source)

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face-mask, joyful roar-state chroma source, one targeted correction
Primary request: Edit Image 1, the sole target and identity anchor, into a joyful compact roar expression. Change only the mouth and subtle brow expression. Replace the tiny closed smile with exactly one small centered rounded O mouth whose entire interior is one uninterrupted, uniform warm deep-plum cavity. Gently lift both brows. Keep both giant honey-brown eyes open and identical to Image 1.
Critical correction: the mouth must contain absolutely no tongue, no lower pink shape, no teeth, no gums, no beak, no uvula, no highlights, and no internal feature of any kind—only one uniform dark warm-plum oval interior from top edge to bottom edge.
Scene/backdrop: preserve the exact same perfectly flat uniform solid green chroma field, with no shadow, gradient, texture, floor, reflection, water, bubbles, or variation.
Identity invariants: keep the exact same Bubbly Octopus identity, rounded coral-purple mantle/head, proportions, placement, scale, silhouette, six-to-eight compact attached curled tentacle tips, suction-cup accents, blush, eyes, plush-clay material, lighting, colors, padding, and all non-expression pixels as visually identical to Image 1 as possible. Do not redesign or move tentacles. Do not change the head contour, skin texture map, cheeks, eye geometry, or backdrop.
Transition requirement: this state will be localized to the compact mouth and two small brow regions and blended over neutral using premultiplied copy-plus-lighter weights, so there must be no skin or tentacle shimmer outside those regions.
Expression geometry: the single O mouth stays well above the tentacle ruff, centered on the face, and substantially narrower than the distance between the inner eye corners. Both brows lift subtly and symmetrically; eyes remain bright, open, friendly, and unchanged.
Constraints: change only mouth and subtle brows; absolutely no tongue or pink shape inside the mouth; no teeth, gums, beak, drool, wide jaw, grin, split mouth, or aggressive snarl; no added props, text, logos, watermark, body, water, bubbles, squid fins, jellyfish cues, detached pieces, green subject detail, shadow, floor, reflection, or new elements. Keep every part fully within frame and the background one removable flat field.
```

## Outputs and audit evidence

- Final chroma masters: `design/runtime/octopus/chroma/{neutral,blink,roar}-v1.png`
- Final shared-alpha masters: `design/runtime/octopus/alpha/{neutral,blink,roar}-v1.png`
- Runtime exports: `public/masks/octopus/{neutral,blink,roar}-v1.webp`
- Byte-identical Pages exports: `github-pages/public/masks/octopus/{neutral,blink,roar}-v1.webp`
- Machine-readable metrics and hashes: `audit/metrics-v1.json`
- State review at 380 and 96 px: `audit/states-native-96-380-v1.png`
- Current premultiplied blend review: `audit/copy-lighter-crossfades-380-v1.png`
- White, black, green, and magenta backdrop review: `audit/hostile-380-states-v1.png`
- Tentacle/suction-cup matte closeups: `audit/tentacle-matte-closeups-v1.png`
- Canonical tracked-face coverage proof: `audit/canonical-forehead-geometry-v1.png`
