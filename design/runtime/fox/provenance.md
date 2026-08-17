# Fantastic Fox v1 provenance

## Route and references

- Generation route: built-in Codex ImageGen.
- Approved style reference: `design/runtime/bumblebee/chroma/neutral-v1.png` (style, finish, composition, scale, padding, and lighting only).
- Neutral generation source: `/Users/kevinbolander/.codex/generated_images/01a00bfa-4f32-78c3-ad4e-5b276de9d9ac/exec-ae316040-5b73-4d4d-b0b9-5b23313ae9c3.png`; durable raw copy: `design/runtime/fox/audit/raw/neutral-generated-v1.png`.
- Blink generation source: `/Users/kevinbolander/.codex/generated_images/01a00bfa-4f32-78c3-ad4e-5b276de9d9ac/exec-1456b189-b8ce-4964-a3d8-a38bf94fc02f.png`; durable raw copy: `design/runtime/fox/audit/raw/blink-generated-v1.png`.
- Roar generation source: `/Users/kevinbolander/.codex/generated_images/01a00bfa-4f32-78c3-ad4e-5b276de9d9ac/exec-22e045a0-6609-413b-8463-7555fdeb5177.png`; durable raw copy: `design/runtime/fox/audit/raw/roar-generated-v1.png`.
- Transparent masters were produced with the installed ImageGen chroma-removal helper using border auto-key, soft matte, thresholds 12/220, and despill.
- Final chroma masters were deterministically recomposited over exact `#00FF00` after alpha validation.
- Blink and roar were composited only through feathered expression ROIs onto the exact neutral anchor. The final alpha channel is byte-identical across all three states.

## Exact prompts

### Neutral

```text
Use case: stylized-concept
Asset type: reactive webcam game animal face mask — neutral anchor
Input images: Image 1 is the approved Bumblebee visual style, finish, composition, scale, padding, and lighting reference only; do not preserve any bee anatomy, colors, stripes, wings, antennae, or scalloped silhouette.
Primary request: Create an original front-facing chibi red fox head as a single clean game mask asset.
Scene/backdrop: perfectly flat, exact solid #00FF00 chroma-key background for local removal. The background must be one absolutely uniform color with no shadow, gradient, texture, reflection, floor plane, halo, or lighting variation.
Subject: unmistakable fox head only: rich red-orange fur; very tall upright triangular ears with deep charcoal-brown tips and pale warm inner fur; angular outward fluffy cheek tufts creating a fox-like diamond silhouette; a tiny centered forehead tuft; cream-white lower face, cheek bib, and compact tapered muzzle; tiny rounded dark nose; warm coral blush; two enormous symmetrical honey-brown eyes with luminous layered irises and clean white catchlights; gently lifted brows; neutral gentle closed smile with no visible teeth.
Style/medium: premium polished 2.5D plush-clay character render matching Image 1’s tactile micro-fuzz, soft rounded forms, crisp expressive facial modeling, subtle dimensional shading, and friendly preschool-safe finish. Soft warm frontal studio lighting only on the subject.
Composition/framing: straight-on, perfectly centered and symmetric, generous even padding around both tall ear tips and all cheek fur, subject fills a comparable portion of the square as the reference without touching edges; complete head silhouette visible. No neck or shoulders.
Color palette: red-orange, cream-white, charcoal-brown, honey-brown, coral; never use #00FF00 or near-key green anywhere inside the fox.
Constraints: preserve the approved reference’s chibi eye-to-face proportion and production polish; fox species must read instantly at 96px through ears, angular cheek silhouette, and compact tapered muzzle; no text, no watermark, no cast/contact shadow, no reflection; one head only.
Avoid: dog, puppy, cat, wolf, coyote ambiguity; round teddy-bear silhouette; short floppy ears; whiskers; body; neck; tail; paws; forest; foliage; ground; props; collar; clothing; fangs; teeth; open mouth; tongue; duplicate features; green pixels in the subject.
```

### Blink

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face mask — blink state
Input images: Image 1 is the sole edit target and exact fox identity anchor.
Primary request: Change only the eye and eyebrow expression into a delighted happy blink: both enormous eyes fully closed as smooth upward-curving dark plush lashes, with friendly slightly lifted brows. Preserve the small neutral closed smile exactly; no open mouth and no teeth.
Constraints: preserve Image 1 exactly everywhere outside the smallest eye-and-brow regions — identical 1254×1254 composition, fox identity, ear and cheek silhouette, forehead tuft, fur texture, all red-orange/cream/dark-tip markings, muzzle, nose, blush, lighting, scale, padding, and exact flat #00FF00 chroma background. Do not redraw, move, recolor, rescale, crop, or relight anything else. Maintain premium 2.5D plush-clay finish. No new elements, text, watermark, body, neck, tail, props, shadow, teeth, tongue, or open mouth. The background stays one exact uniform #00FF00 and the subject contains no key green.
```

### Roar

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face mask — roar state
Input images: Image 1 is the sole edit target and exact fox identity anchor.
Primary request: Change only the mouth and eyebrows into a delighted child-safe little roar: compact centered rounded O mouth beneath the nose, dark warm mouth interior with one small warm coral tongue low inside, absolutely no teeth or fangs; gently lift both brows. Keep both enormous honey-brown eyes fully open and preserve their size, gaze, irises, and catchlights.
Constraints: preserve Image 1 exactly everywhere outside the smallest mouth-and-brow regions — identical 1254×1254 composition, fox identity, ear and cheek silhouette, forehead tuft, fur texture, all red-orange/cream/dark-tip markings, muzzle, nose, blush, open eyes, lighting, scale, padding, and exact flat #00FF00 chroma background. Do not redraw, move, recolor, rescale, crop, or relight anything else. Maintain premium 2.5D plush-clay finish. No new elements, text, watermark, body, neck, tail, props, shadow, teeth, or fangs. The background stays one exact uniform #00FF00 and the subject contains no key green.
```

## Export and audit notes

- Runtime WebP settings: quality 95, method 6, exact alpha; 276,112–279,702 bytes per state.
- Alpha bbox for every state: `(101, 147, 1151, 1118)`; padding: left 101, top 147, right 103, bottom 136 pixels.
- Alpha-weighted centroid for every state: `(624.57, 655.46)`; alpha coverage: `0.473586`.
- Transparent/partial pixels per state: 824,960 / 3,795; all four corners are alpha 0.
- Alpha channels are byte-identical across neutral, blink, and roar (`7312285232e4a2cf6fe93087c2920d3bb4a2fd594d12e55451912c88c8c114dc`).
- Subject mask has one connected component and zero enclosed transparent holes at alpha threshold 12.
- Green-fringe scan found zero partially transparent pixels with green exceeding both red and blue by more than 20.
- Public and GitHub Pages copies are byte-identical for all three states.
- Native, 380px hostile-background, 96px thumbnail, and 0/25/50/75/100 current copy-plus-lighter transition audits are in `design/runtime/fox/audit/`.
- Independent Gauntlet approval is intentionally deferred to a separate critic.
