# Sleepy Sloth v1 provenance

Generation route: built-in ImageGen. No CLI/API fallback was used. No generated state was retried.

Reference image:

- `design/runtime/bumblebee/chroma/neutral-v1.png` — finish and composition reference only.

Durable generated sources:

- `design/runtime/sloth/audit/generated-neutral-v1.png`
- `design/runtime/sloth/audit/generated-blink-v1.png`
- `design/runtime/sloth/audit/generated-roar-v1.png`

Original built-in ImageGen saves:

- `/Users/kevinbolander/.codex/generated_images/01a00c1b-ba37-7c43-9603-0b3c154f1178/exec-46ea1cd5-6ea1-4f6e-a04b-8ce9f64d239f.png`
- `/Users/kevinbolander/.codex/generated_images/01a00c1b-ba37-7c43-9603-0b3c154f1178/exec-ab45de16-dcec-4309-81f9-6412f4a9b45a.png`
- `/Users/kevinbolander/.codex/generated_images/01a00c1b-ba37-7c43-9603-0b3c154f1178/exec-6bece6d5-52c2-4189-8e80-8534d252902e.png`

## Neutral prompt

```text
Use case: stylized-concept
Asset type: reactive children's browser game face-mask state, neutral anchor
Primary request: Create one unmistakable unlabeled sleepy sloth head in the same premium chibi finish, framing discipline, and tactile 2.5D plush-clay rendering quality as Image 1. Image 1 is a finish/composition reference only; do not copy its animal anatomy, colors, antennae, wings, stripes, or silhouette.
Scene/backdrop: perfectly flat, exact solid #00FF00 chroma-key background for local removal; one uniform color corner-to-corner with no floor plane, shadow, gradient, texture, reflection, glow, vignette, or lighting variation.
Subject: a single front-facing chibi sloth head only, warm taupe and cocoa-brown shaggy plush fur, softly rounded crown, gentle cheek fluff, one pale cream facial disk and compact muzzle, two symmetrical dark chocolate sloth eye-mask patches sweeping outward from the eyes, a small dark rounded nose, soft peach blush, and two enormous glossy honey-brown eyes with bright catchlights. Neutral expression: calm tiny closed smile, relaxed friendly brows, mouth closed, absolutely no teeth.
Style/medium: premium kid-safe 2.5D plush-clay character render with longer soft micro-fur and tactile handcrafted detail, matching Image 1's polish, warmth, rounded chibi proportions, giant expressive eye scale, and crisp isolated game-asset finish.
Composition/framing: square image; one centered, nearly symmetrical, straight-on head; head fills roughly 78–82% of canvas width and height with generous even padding on all four sides; full fur silhouette completely inside frame; no cropped fibers or features.
Lighting/mood: soft frontal studio illumination contained entirely on subject; sleepy, sweet, welcoming, playful.
Color palette: warm taupe, cocoa brown, pale cream, dark chocolate, honey amber, subtle peach blush. Do not use #00FF00 or bright green anywhere in the subject.
Materials/textures: longer plush micro-fur on the brown head and cheek silhouette; facial disk softly velvety; eyes glossy glass-like; nose softly clay-polished. Keep fur readable but not photorealistic or stringy.
Constraints: head only; preserve clean child-safe silhouette; no body, neck, shoulders, arms, hands, branch, leaf, props, environment, clothing, accessories, labels, text, logo, watermark, cast shadow, contact shadow, reflection, or transparent areas. Neutral mouth must stay a small closed smile with no visible teeth or tongue.
Avoid: teddy bear, raccoon, koala, monkey, owl, human face, muzzle beard, side view, tilted pose, realism, horror, sleepy cap, extra facial markings, asymmetrical eye masks, open mouth, fangs, hard plastic, flat vector art, chroma inside subject.
```

## Blink prompt

```text
Use case: identity-preserve
Asset type: reactive children's browser game face-mask state, blink
Input images: Image 1 is the sole edit target and identity anchor.
Primary request: Change only the expression of Image 1 into the sloth's happy sleepy blink state.
Subject edit: both enormous eyes are fully closed into clean soft downward-curving eyelids with short child-safe lashes; the calm little closed smile becomes just slightly happier; brows may relax subtly. Keep the mouth closed with no teeth and no tongue.
Preserve exactly: the same single front-facing sloth identity, head silhouette and scale, exact position and crop, shaggy warm taupe/cocoa fur, every outer fur edge, pale cream facial disk and muzzle, symmetrical dark eye-mask patches and their exact shapes, nose, blush, proportions, lighting, palette, material finish, and the exact flat solid #00FF00 background. Keep both eye-mask patches fully dark and stable around the closed eyes.
Constraints: change only the compact eye-expression region and tiny smile curve; do not regenerate, repaint, restyle, move, resize, rotate, crop, or alter the head, fur, eye masks, muzzle, cheeks, nose, background, or lighting. No body, arms, branch, leaf, props, text, logo, watermark, shadows, gradients, floor, reflection, or chroma inside the subject.
Avoid: open eyes, half-open eyes, winking, asymmetry, new markings, green spill, teeth, tongue, open mouth, sad expression, angry brows, eyelid highlights that look like open eyes.
```

## Roar prompt

```text
Use case: identity-preserve
Asset type: reactive children's browser game face-mask state, roar
Input images: Image 1 is the sole edit target and identity anchor.
Primary request: Change only the expression of Image 1 into a slow delighted child-safe sloth roar/yawn state.
Subject edit: replace only the tiny closed smile with one compact vertical rounded O-shaped open mouth centered under the nose; mouth interior warm dark cocoa, with a small warm pink tongue visible low inside; absolutely no teeth or fangs. Keep both enormous honey-brown eyes open and recognizable, with softly lifted brows and a mildly delighted sleepy expression.
Preserve exactly: the same single front-facing sloth identity, head silhouette and scale, exact position and crop, shaggy warm taupe/cocoa fur, every outer fur edge, pale cream facial disk and muzzle, symmetrical dark eye-mask patches and their exact shapes, giant eyes, nose, blush, proportions, lighting, palette, material finish, and exact flat solid #00FF00 background.
Constraints: change only the compact mouth region and a subtle brow lift; do not regenerate, repaint, restyle, move, resize, rotate, crop, or alter the head, fur, eye masks, eyes, muzzle, cheeks, nose, background, or lighting. Mouth must be compact and centered, not a huge scream. No body, arms, branch, leaf, props, text, logo, watermark, shadows, gradients, floor, reflection, or chroma inside the subject.
Avoid: teeth, fangs, beak, human mouth, wide scream, oversized mouth, distorted cheeks, angry eyes, closed eyes, asymmetry, new markings, green spill, drool, horror, extra tongue, uvula.
```

## Deterministic processing

- `build_export_audit.py` removes the neutral chroma field with the installed helper using soft matte, despill, and one-pixel edge contraction.
- Blink and roar RGB edits are feather-localized onto neutral, clipped to the safe alpha interior, and assigned the exact neutral alpha plane.
- Runtime exports use WebP q95, alpha quality 100, method 6, and exact RGB under transparency at 1024 square.
- `manifest-v1.json` records checksums, candidate weights, geometry, alpha parity, and copy parity.
