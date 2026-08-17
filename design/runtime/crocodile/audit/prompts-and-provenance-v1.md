# Chomp-Chomp Crocodile v1 prompts and provenance

Generation route: built-in ImageGen. The approved Bumblebee v1 neutral was used only as a finish/composition reference for the new neutral. Blink and roar used the generated crocodile neutral as their sole edit target. The green subject was generated on a removable `#FF00FF` field and extracted with the installed ImageGen chroma helper using soft matte, despill, and one-pixel edge contraction.

## Neutral

```text
Use case: stylized-concept
Asset type: reactive browser game animal face-mask state, neutral anchor
Input images: Image 1 is a finish, lighting, material, composition, and quality reference only. Do not copy its bee anatomy, colors, stripes, wings, antennae, or silhouette.
Primary request: Create an original front-facing chibi crocodile face/head named Chomp-Chomp Crocodile, isolated on a perfectly flat solid #FF00FF magenta chroma-key background for local background removal.
Subject: unmistakably crocodilian moss-green to emerald-green head only; broad low armored cranium; long-but-contained blunt crocodile snout filling the lower face; softly pebbled and scuted plush-clay skin; raised eye ridges with two giant symmetrical honey-brown glossy eyes; two distinct nostrils near the snout tip; small side cheek scales; warm coral blush. Neutral expression is a gentle small closed smile with absolutely no visible teeth.
Style/medium: premium polished 2.5D plush-clay character render matching Image 1's adorable rounded chibi proportions, tactile microtexture, soft studio modeling, glossy eyes, and production quality.
Composition/framing: straight-on, perfectly centered, bilateral symmetry, opaque full-face coverage, generous even padding on all sides, head and snout fully contained; no neck, body, tail, or cropped features.
Lighting/mood: warm playful child-safe joy, soft frontal studio illumination on the subject only.
Constraints: background must be one exact uniform #FF00FF field with no shadows, gradients, texture, floor plane, reflections, or lighting variation; crisp clean silhouette; do not use magenta anywhere in the subject; no cast/contact shadow; no text, labels, logo, or watermark.
Avoid: alligator cartoon body, generic lizard, dragon, dinosaur, scary realism, fangs, rows of teeth, open mouth, tongue, water, plants, props, scene, border, duplicate facial features.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c74-b529-7f12-afd3-916ce82d815e/exec-463f01cc-d2fd-431e-8490-b74ebc509b5e.png`

## Blink

```text
Use case: precise-object-edit
Asset type: reactive browser game animal face-mask state, blink
Input images: Image 1 is the sole edit target and exact identity anchor.
Primary request: Change only both eyes and the tiniest immediately adjacent eyelid area so this exact crocodile performs a bilateral happy blink. Replace both open eyes with matching gently upward-curved closed eyelid arcs, with a subtle lifted-cheek happy expression. Keep the neutral small closed smile unchanged and keep zero visible teeth.
Constraints: preserve the exact same crocodile identity, species markers, broad armored cranium, snout geometry, nostrils, cheek scales, blush, silhouette, pose, centered framing, scale, green color palette, surface texture, highlights, lighting, and exact uniform #FF00FF background. The background must remain one flat solid #FF00FF field with no shadows, gradients, texture, floor, reflections, or variation. No magenta in the subject. No body, neck, tail, water, props, text, logo, or watermark.
Avoid: one eye open, changed mouth, teeth, open mouth, scary expression, anatomy redesign, shifted/cropped head, new scales, recoloring, style drift, duplicate features.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c74-b529-7f12-afd3-916ce82d815e/exec-5289da40-ea2a-47c5-92cb-6580b51642a6.png`

## Roar

```text
Use case: precise-object-edit
Asset type: reactive browser game animal face-mask state, child-safe roar
Input images: Image 1 is the sole edit target and exact identity anchor.
Primary request: Change only the mouth opening and the immediately adjacent lower-snout expression area so this exact crocodile makes a playful child-safe roar. Replace the neutral closed smile completely with one compact, centered, rounded open mouth contained well inside the blunt snout. Mouth cavity is one simple uniform warm deep-coral/burgundy surface with a small soft tongue shape and exactly FOUR tiny blunt rounded cream teeth total: two top and two bottom, evenly spaced. Lift both eye ridges slightly while keeping both giant honey-brown eyes open and unchanged. The result should read delighted, never scary.
Constraints: preserve the exact same crocodile identity, broad armored cranium, eye identity, snout geometry, nostrils, cheek scales, blush, silhouette, pose, centered framing, scale, green palette, surface texture, highlights, lighting, and exact uniform #FF00FF background. The background must remain one flat solid #FF00FF field with no shadows, gradients, texture, floor, reflections, or variation. Remove the original closed smile; only one mouth may exist. Exactly four tiny blunt rounded teeth maximum, no other teeth. No magenta in subject. No body, neck, tail, water, props, text, logo, or watermark.
Avoid: rows of teeth, fangs, pointed teeth, big jaw gape, scary grin, separate smile under or beside open mouth, dark cavernous throat, duplicate mouth, asymmetrical eyes, anatomy redesign, shifted/cropped head, recoloring, style drift.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c74-b529-7f12-afd3-916ce82d815e/exec-0f5d2be6-0313-4916-87ba-e95c6ed29f2e.png`

## Deterministic finishing

- Generated sources are preserved as `design/runtime/crocodile/audit/generated-*-v1.png`.
- Canonical chroma files are localized, alpha-locked composites on exact `#FF00FF`, not raw expression generations.
- Neutral controls the silhouette and every non-expression pixel. Blink is localized to the paired eye interiors; roar is localized to the mouth/lower-snout region.
- All three 1254 × 1254 alpha masters and runtime exports share an identical alpha-pixel hash.
- Runtime exports are 1254 px WebP, quality 94, alpha quality 100, method 6, exact alpha: neutral 325,104 bytes; blink 337,908 bytes; roar 308,724 bytes.
- Alpha bbox is `[81, 189, 1175, 1089]`, with padding `[81, 189, 79, 165]`, transparent corners, zero enclosed transparent holes, and zero magenta-dominant partial-alpha pixels.
- The current three-state copy+lighter compositor is audited over simultaneous blink/roar weights. The smile and roar share a single mouth region, so no separate semantic roar midpoint is required.
