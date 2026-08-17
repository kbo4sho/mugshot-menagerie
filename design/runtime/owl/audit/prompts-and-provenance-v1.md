# Winky Owl v1 — prompts and provenance

## Generation route

- Route: built-in Codex ImageGen.
- Approved finish/composition reference for neutral only: `design/runtime/bumblebee/alpha/neutral-v1.png`.
- Neutral ImageGen source: `/Users/kevinbolander/.codex/generated_images/01a00c11-fc7e-7f33-bf07-63be2d2dc8c7/exec-83083d25-eee9-4a1d-859c-5f2c4d15dae1.png`.
- Blink ImageGen source: `/Users/kevinbolander/.codex/generated_images/01a00c11-fc7e-7f33-bf07-63be2d2dc8c7/exec-725f0dbd-34be-4946-9ed2-85e83ae72137.png`.
- Roar ImageGen source: `/Users/kevinbolander/.codex/generated_images/01a00c11-fc7e-7f33-bf07-63be2d2dc8c7/exec-f3eb3532-3a13-4a86-8eff-c127fab8eb7e.png`.
- Durable copies of all three raw outputs: `design/runtime/owl/audit/generated-{neutral,blink,roar}-v1.png`.
- Blink and roar each used the neutral source as their sole edit target. No state-to-state chaining.
- No ImageGen retry was used. Neutral chroma extraction received one permitted local `--edge-contract 1` refinement after the default soft-matte audit showed a thin keyed rim.

## Neutral prompt

```text
Use case: stylized-concept
Asset type: Giggle Zoo reactive webcam game animal mask, neutral state source
Primary request: Create one completely original Winky Owl neutral-state character head, using Image 1 only as the approved finish, chibi proportion, lighting, material, padding, and centered composition reference. Do not copy any bee anatomy, stripes, antennae, wings, silhouette, or colors.
Scene/backdrop: perfectly flat, exact, uniform solid #00FF00 chroma-key field filling every pixel outside the subject; absolutely no gradient, texture, vignette, shadows, reflections, glow, or floor plane.
Subject: unmistakable front-facing chibi owl head only. Warm cocoa-brown rounded owl silhouette with two small soft ear tufts; broad cream heart-shaped facial disk formed as two symmetrical cream lobes around the eyes and tapering gently toward the beak; giant glossy honey/amber eyes with dark pupils and bright catchlights; compact golden triangular beak precisely centered between and just below the eyes; subtle darker cocoa forehead feather chevrons; tiny peach blush ovals. No body, shoulders, neck, wings, feet, branch, moon, scenery, clothing, props, or labels. Neutral expression is gentle and friendly: eyes wide open, beak closed with a tiny soft smile read.
Style/medium: premium 2.5D chibi plush-clay character render with soft feather microtexture, rounded handcrafted forms, clean high-end mobile game asset finish matching Image 1's quality without copying its design.
Composition/framing: perfectly front-facing, bilaterally symmetrical, centered square close-up; head fills roughly 80–84% of canvas width and 72–78% of height; generous transparent-safe padding on every side; both ear tufts fully inside frame; no crop.
Lighting/mood: soft warm frontal studio illumination contained entirely on the subject; playful, safe, sweet, child-friendly.
Color palette: warm cocoa and espresso browns, creamy ivory facial disk, honey/amber irises, compact golden beak, subtle peach blush. Do not use #00FF00 or green anywhere inside the owl.
Materials/textures: plush short feather nap and soft clay-like dimensional shaping, controlled low-frequency texture, crisp clean silhouette suitable for chroma extraction.
Constraints: one owl head only; no text, watermark, logo, badge, border, frame, cast shadow, contact shadow, ground, or background decoration. Outside-subject background must be exactly uniform #00FF00. Keep all subject edges clean and fully separated from the background with generous padding. Avoid semi-transparent wisps or loose floating feathers.
```

## Blink prompt

```text
Use case: precise-object-edit
Asset type: Giggle Zoo reactive webcam game animal mask, blink state source
Input images: Image 1 is the sole edit target and identity anchor: approved Winky Owl neutral-state chroma source.
Primary request: Create the bilateral happy blink expression from Image 1. Change only the eyes and the minimum immediately surrounding eyelid/eyebrow-feather region needed for a natural blink. Both eyes must be fully closed as matching cheerful upward-curving arcs. Add a subtly lifted, delighted brow-feather read while retaining the same gentle closed golden beak and tiny smile.
Constraints: Preserve the exact same owl identity, species, silhouette, head size and placement, ear tufts, cocoa plumage, cream heart-shaped facial disk, forehead chevrons, golden beak, cheek blush, lighting direction, plush-clay feather microtexture, camera, crop, padding, and exact uniform #00FF00 background. Do not redesign, reposition, rotate, rescale, crop, or relight the head. Do not alter the beak or mouth. Do not add body, wings, props, scenery, text, logo, watermark, shadow, reflection, glow, floor, or background variation. Do not use green inside the subject.
Transition requirement: This state will be blended over the neutral state using premultiplied copy-plus-lighter weights, so all pixels outside the localized eye/brow expression region should remain as visually identical to Image 1 as possible, without feather-map shimmer or texture drift.
Avoid: one-eye wink; open or half-open eyes; eyelashes; teeth; tongue; new ornaments; any change to outer silhouette or facial disk.
```

## Roar prompt

```text
Use case: precise-object-edit
Asset type: Giggle Zoo reactive webcam game animal mask, roar state source
Input images: Image 1 is the sole edit target and identity anchor: approved Winky Owl neutral-state chroma source.
Primary request: Create a delighted vocalizing roar expression from Image 1. Change only the compact golden beak/mouth and the minimum immediately surrounding brow-feather region needed for expression. Lift the brow feathers slightly for happy surprise while keeping both giant honey/amber eyes fully open. Open the beak into one small, safe, rounded vertical O centered at the exact same beak location; keep a golden beak rim and reveal only a simple warm pink mouth interior. No teeth, fangs, tongue, split second beak, or dark scary cavity.
Constraints: Preserve the exact same owl identity, species, silhouette, head size and placement, ear tufts, cocoa plumage, cream heart-shaped facial disk, forehead chevrons, giant open amber eyes and catchlights, cheek blush, lighting direction, plush-clay feather microtexture, camera, crop, padding, and exact uniform #00FF00 background. Do not redesign, reposition, rotate, rescale, crop, or relight the head. Do not close or move the eyes. Do not add body, wings, props, scenery, text, logo, watermark, shadow, reflection, glow, floor, or background variation. Do not use green inside the subject.
Transition requirement: This state will be blended over the neutral state using premultiplied copy-plus-lighter weights, so all pixels outside the localized mouth/beak and subtle brow expression regions should remain as visually identical to Image 1 as possible, without feather-map shimmer or texture drift.
Avoid: large gaping mouth; separate mouth below the beak; multiple beaks; teeth; fangs; tongue; aggressive expression; closed eyes; extra facial marks; any change to outer silhouette or facial disk.
```

## Post-processing and deterministic exports

- Background removal used the installed ImageGen helper with auto-key border sampling, soft matte, thresholds 12/220, and despill. The accepted neutral matte used `--edge-contract 1`.
- `design/runtime/owl/audit/export_and_audit.py` localizes expression RGB to the blink eye islands and roar beak/subtle upper-eye islands, forces the exact neutral alpha onto all states, and rebuilds exact `#00FF00` chroma masters.
- The shared states receive one deterministic centered 1.08× scale normalization so the measured subject reaches 83.7% of canvas width and 73.2% of canvas height while retaining 102 px side padding and at least 166 px vertical padding.
- Runtime exports use WebP quality 95, alpha quality 100, method 6, exact mode, at 1254×1254.
- Published copies: `public/masks/owl/{neutral,blink,roar}-v1.webp`.
- GitHub Pages copies: `github-pages/public/masks/owl/{neutral,blink,roar}-v1.webp`.
- Measurements and SHA-256 provenance: `design/runtime/owl/audit/manifest-v1.json`.
- Review evidence: `states-380-and-96-v1.png`, `copy-lighter-crossfades-380-v1.png`, `hostile-380-states-v1.png`, and `feather-edge-closeups-v1.png` in this directory.
