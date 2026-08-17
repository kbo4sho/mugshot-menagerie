# Color-Pop Chameleon v1 prompts and provenance

Generation route: built-in ImageGen. The approved Bumblebee v1 neutral was used only as a finish/composition reference for the neutral generation. Every expression used the generated chameleon neutral as its sole edit target. The subject was generated on a uniform `#FF00FF` field because the character is green; local alpha extraction used the installed ImageGen chroma-key helper with soft matte, despill, and one-pixel edge contraction.

## Neutral

```text
Use case: stylized-concept
Asset type: reactive webcam game animal mask, neutral state
Input images: Image 1 is the approved Bumblebee finish/composition reference only; preserve its premium 2.5D plush-clay material quality, face-filling chibi proportions, huge glossy honey-brown irises, centered symmetry, lighting softness, and generous clean isolation, but do not copy bee anatomy.
Scene/backdrop: perfectly flat, perfectly uniform solid #FF00FF magenta chroma-key field edge-to-edge for local background removal; no floor plane, no shadow, no gradient, no texture, no lighting variation.
Primary request: create one unmistakable front-facing Color-Pop Chameleon head/face as a polished kid-safe webcam mask.
Subject: compact lime-and-turquoise chameleon head only, no neck or body; softly sculpted casque/crown ridge at top; subtle pebbled plush-clay skin; two large symmetrical chameleon turret-eye domes integrated into the head with giant glossy honey-brown irises looking forward; gently curled side cheek contours; subtle coral, teal, and warm-yellow gradient spots that never use magenta; tiny paired nostrils; soft peach blush; tiny closed happy smile with no visible teeth. The silhouette must read chameleon rather than frog or generic lizard.
Style/medium: premium chibi 2.5D plush-clay character render matching Image 1's tactile soft sculptural quality, not flat vector art.
Composition/framing: single head centered, straight-on, exact bilateral balance, fills roughly 78–84% of the square with generous even padding on all sides, fully opaque forehead/casque, nothing cropped.
Lighting/mood: soft bright studio lighting on the subject only, playful, safe, immediate, joyful.
Constraints: no body, no tail, no branch, no tongue, no insects, no props, no labels, no text, no watermark; no cast shadow, contact shadow, reflection, glow, or floor; crisp clean perimeter; do not use #FF00FF or near-magenta anywhere inside the subject; no green spill into the background; closed smile, no teeth; both eyes fully open and symmetric.
Avoid: frog face, gecko body, snake, photoreal reptile, scary expression, rough spikes, open mouth, asymmetrical pupils, tiny eyes, extra eyes, eyelashes, accessories, background objects.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c67-ca58-7c83-b897-7460f2a03aa0/exec-aafe8b73-2442-417c-964b-3921c1e2ed03.png`

## Blink

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal mask, blink state
Input images: Image 1 is the sole edit target and exact chameleon identity anchor.
Primary request: change only the expression so BOTH turquoise chameleon turret eyes are fully closed as thick, soft, happy upward-curving arcs. The closed lids should retain the exact turquoise pebbled plush-clay material and occupy the same eye-dome positions. Keep a tiny content closed smile and the same cheerful cheeks.
Scene/backdrop: preserve the perfectly flat, uniform solid #FF00FF magenta chroma-key field exactly; no floor, shadow, gradient, texture, or lighting variation.
Constraints: preserve exactly the head silhouette, casque height and ridge, scale, framing, location, lime/turquoise palette, every colored spot and scale texture outside the eye interiors, tiny nostrils, blush, cheeks, lighting, materials, and background from Image 1; edit only the eyes into fully closed happy arcs with no visible iris, pupil, sclera, or lashes; preserve the mouth as the exact same tiny closed smile; no open mouth; no teeth; no tongue; no new objects, body, tail, branch, insect, prop, text, label, watermark, shadow, or magenta pixels in the subject; do not crop.
Avoid: one eye open, wink, sleepy half-open lids, eyelashes, extra brows, moved spots, changed silhouette, frog redesign, angry expression.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c67-ca58-7c83-b897-7460f2a03aa0/exec-4b35fba8-4f3b-4fd9-a5e1-66a523cbf8e4.png`

## Semantic roar midpoint

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal mask, semantic roar midpoint state
Input images: Image 1 is the sole edit target and exact chameleon identity anchor.
Primary request: change only the mouth from the tiny closed smile into a very small, centered, gently open rounded-oval "oh!" mouth in the exact same mouth position. The opening should be clearly open but intermediate between the neutral smile and a full roar: about half the final roar height, with one uniform warm dark cocoa-coral cavity and a subtle lime lip rim. Keep both giant honey-brown irises fully open, forward-facing, and symmetric. Keep the rest of the expression cheerful and safe.
Scene/backdrop: preserve the perfectly flat, uniform solid #FF00FF magenta chroma-key field exactly; no floor, shadow, gradient, texture, or lighting variation.
Constraints: preserve exactly the head silhouette, tall casque and ridge, scale, framing, location, lime/turquoise palette, every colored spot and pebbled skin texture outside the compact mouth region, eye domes and eyes, tiny nostrils, blush, cheeks, lighting, materials, and background from Image 1; edit only the mouth; mouth must be one small clean rounded oval located where the smile was, with no remaining smile line, no tongue, no teeth, no gums, no black void; no body, tail, branch, insect, prop, text, label, watermark, shadow, or magenta pixels in the subject; do not crop.
Avoid: smile plus separate oval, double mouth, huge mouth, tongue, teeth, scary expression, changed eyes, changed spots, changed silhouette, frog redesign, asymmetry.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c67-ca58-7c83-b897-7460f2a03aa0/exec-7e2ebede-3348-4bf7-8609-f1a34b065460.png`

## Roar

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal mask, roar state
Input images: Image 1 is the sole edit target and exact chameleon identity anchor.
Primary request: change only the expression into a joyful kid-safe chameleon roar: replace the tiny smile with one compact centered rounded O-shaped open mouth below the nostrils, with a smooth uniform warm dark cocoa-coral mouth cavity. No tongue and no teeth. Slightly lift the upper eye-dome brows/casque expression while keeping both giant honey-brown irises fully open, forward-facing, and symmetric.
Scene/backdrop: preserve the perfectly flat, uniform solid #FF00FF magenta chroma-key field exactly; no floor, shadow, gradient, texture, or lighting variation.
Constraints: preserve exactly the head silhouette, casque height and ridge, scale, framing, location, lime/turquoise palette, every colored spot and scale texture outside the compact mouth and immediate brow expression regions, eye identity, tiny nostrils, blush, cheeks, lighting, materials, and background from Image 1; edit only the compact mouth and subtle brow expression; mouth must be a single small rounded O with one uniform warm cavity and a clean lip rim, not a huge jaw split; no tongue; no teeth; no gums; no body, tail, branch, insect, prop, label, text, watermark, shadow, or magenta pixels in the subject; do not crop.
Avoid: tongue, teeth, split jaw, huge mouth, black void, scary expression, extra nostrils, changed pupils, changed spots, changed silhouette, frog redesign, asymmetry.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c67-ca58-7c83-b897-7460f2a03aa0/exec-c9809ecf-89a7-4ceb-b90c-244bcac709d5.png`

## Deterministic finishing

- Generated sources are preserved as `design/runtime/chameleon/audit/generated-*-v1.png`.
- Canonical `design/runtime/chameleon/chroma/*-v1.png` files are the localized, alpha-locked states composited over uniform `#FF00FF`.
- The neutral alpha is shared byte-for-byte across all four alpha masters and all four runtime exports.
- Blink changes are localized to the two turret-eye interiors; roar states are localized to the compact mouth region.
- Runtime exports are full-size 1254 px WebP, quality 95, alpha quality 100, method 6, exact alpha.
