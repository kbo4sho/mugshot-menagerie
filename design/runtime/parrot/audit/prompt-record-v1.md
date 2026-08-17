# Party Parrot v1 prompt record

Generation route: built-in ImageGen. Bumblebee v1 was inspected as a finish/composition reference only and was not used as an edit target. Blink and roar used Party Parrot's generated neutral as their sole edit target.

## Neutral generation

```text
Use case: stylized-concept
Asset type: reactive webcam animal face-mask game character, neutral state master
Primary request: Create an original front-facing chibi parrot head named “Party Parrot,” unmistakably a parrot and designed to cover a child’s full face.
Scene/backdrop: perfectly flat, solid, uniform #00FF00 chroma-key background for local removal; no floor plane.
Subject: one centered parrot head only. Broad rounded scarlet-red feather crown and head with solid forehead coverage; subtle short crest tuft; symmetrical golden-yellow cheek patches; compact cobalt-blue side-feather accents; one large compact curved parrot beak centered low between the eyes, pale warm ivory/horn upper beak with a small charcoal tip and a subtle lower-beak seam. Giant glossy honey-brown eyes with creamy sclera, friendly brows, warm coral blush, and a calm neutral closed-beak smile. The eyes should dominate the face while the beak remains clearly parrot-specific. No body, neck, shoulders, wings, perch, pirate gear, hat, costume, fruit, props, labels, or scenery.
Style/medium: premium 2.5D chibi plush-clay character render; soft tactile short feather microtexture and sculpted clay volumes; polished family game art. Match this production finish: huge expressive glossy eyes, rounded compact facial proportions, warm internal shading, crisp full silhouette, gentle studio highlights, rich but controlled color, lovable preschool-safe personality.
Composition/framing: square 1:1 canvas, perfectly front-facing and bilaterally balanced, centered, generous even transparent-ready padding around the outer silhouette, entire crown/crest/beak visible, no crop. The head should fill roughly 76–82% of canvas width and 72–78% height, with a stable single connected silhouette.
Lighting/mood: bright soft frontal studio lighting restricted to subject; joyful, sweet, inviting; no scary aggression.
Materials/textures: scarlet plush-feather microtexture, smooth semi-matte horn beak, golden cheek feathers, cobalt accent feathers, glassy honey-brown irises. Keep texture subtle enough to remain stable during expression animation.
Constraints: background must be exact flat #00FF00 with no shadow, gradient, texture, reflection, vignette, ambient spill, or lighting variation. Do not use #00FF00 or near-key green anywhere inside the subject. Crisp clean outer edge with no wispy feathers. No cast/contact shadow. No text, logo, watermark. Neutral state only: both eyes fully open; beak fully closed and friendly.
Avoid: photoreal bird anatomy, long pointed beak, chicken/duck/toucan read, angry eyes, teeth, tongue, body, wings, feet, props, costume, asymmetry, floor shadow, environmental lighting, fuzzy edge strands.
```

## Neutral framing retry

```text
Use case: precise-object-edit
Asset type: reactive webcam animal face-mask game character, neutral state master
Input images: Image 1 is the sole edit target, the exact approved Party Parrot character.
Primary request: Change only framing and backdrop. Preserve this exact parrot’s identity, face design, scarlet/golden/cobalt feather map, eyes, brows, blush, beak geometry, material finish, lighting, symmetry, neutral expression, and all internal details. Uniformly scale the entire complete parrot head down and center it so the outer silhouette occupies about 78% of the square canvas width and about 78% height, leaving at least 11% clear background padding on every side. Keep every feather tip, crest, cheek feather, beak and chin fully visible.
Scene/backdrop: replace transparent/black background pixels with a perfectly flat solid uniform exact #00FF00 chroma-key field.
Constraints: change only framing and backdrop; keep the character pixel-faithful in design and color. No new feathers, no body, no wings, no props, no text, no watermark, no floor, no cast/contact shadow. Background must be exact #00FF00 everywhere outside the subject with no gradient, texture, vignette, lighting variation, or spill. Do not introduce #00FF00 inside the subject. Keep crisp clean edges and generous even padding.
```

## Blink edit

```text
Use case: identity-preserve
Asset type: reactive webcam animal face-mask game character, blink state
Input images: Image 1 is the sole edit target and exact Party Parrot neutral-state master.
Primary request: Change only the expression into a joyful bilateral blink. Replace both open eyes with large, symmetric, gently upturned closed-eye arcs nestled in the exact same eye sockets; slightly lift and soften both brows. Keep the friendly beak completely closed with its exact neutral shape.
Constraints: preserve the exact character identity, canvas, scale, position, outer silhouette, crest, every scarlet/golden/cobalt feather region, feather map, cheeks, blush, beak geometry and color, lighting, texture, padding, and #00FF00 chroma backdrop. Change only both eyes and minimally the brows. Keep perfect bilateral expression symmetry. No mouth opening, no tongue, no teeth, no new elements, no body, no text, logo, watermark or shadow. Background remains perfectly flat exact #00FF00.
Avoid: winking, asymmetrical lids, squeezed/scary expression, beak change, feather drift, recolor, crop, camera change, floor or environmental detail.
```

## Roar edit

```text
Use case: identity-preserve
Asset type: reactive webcam animal face-mask game character, roar state
Input images: Image 1 is the sole edit target and exact Party Parrot neutral-state master.
Primary request: Change only the expression into a playful child-safe parrot “roar.” Open the compact beak into a small centered rounded O/trumpet shape: preserve the exact pale horn upper beak and charcoal tip, lift it only slightly, reveal one continuous warm dark coral mouth cavity, and add a compact lower horn beak below so the overall beak silhouette stays tight. Slightly lift both brows and keep both giant eyes fully open and joyful.
Constraints: preserve the exact character identity, canvas, scale, position, outer silhouette, crest, every scarlet/golden/cobalt feather region, feather map, cheeks, blush, eye design, lighting, texture, padding, and #00FF00 chroma backdrop. Change only the beak/mouth opening and minimally the brows. The open cavity must be continuous, centered, clearly semantic at thumbnail size, warm and friendly. Absolutely no teeth and no tongue. No scary aggression, no body, no new elements, no text, logo, watermark or shadow. Background remains perfectly flat exact #00FF00.
Avoid: teeth, tongue, split/disconnected mouth cavity, doubled beak, mammal mouth, huge gape, hooked weapon-like beak, angry brows, eye drift, feather drift, recolor, crop, camera change, floor or environmental detail.
```

## Roar cavity retry

```text
Use case: precise-object-edit
Asset type: reactive webcam animal face-mask game character, roar state correction
Input images: Image 1 is the sole edit target and exact Party Parrot roar state.
Primary request: Change only the open beak cavity. Make the gape about 25% shorter vertically and read as a compact rounded O. Replace all bright red inner shapes and any tongue-like central form with one continuous, simple, uniform deep warm burgundy mouth cavity. Keep the pale horn lower beak compact, symmetrical, and clearly separate from the cavity.
Constraints: absolutely no tongue, no teeth, no uvula, no interior lobe, no split cavity. Preserve every other pixel-level design decision: exact parrot identity, eyes, lifted brows, face, feather map, crest, scale, position, silhouette, upper beak shape/charcoal tip, colors, texture, lighting, padding, and flat green background. No crop, no new elements, no text, logo, watermark or shadow.
```

## Deterministic finishing

- Removed chroma locally with the installed ImageGen helper using border auto-key, soft matte, thresholds 12/220, and despill.
- Localized blink to the eye sockets/brows and explicitly guarded the neutral beak.
- Localized roar to the beak opening and lifted brows.
- Locked every state to the exact neutral alpha mask, normalized chroma masters to exact `#00FF00`, and applied the same 1.106× canonical framing correction to all states for 78.15% width coverage.
- Exported runtime WebPs at 1344×1344, quality 95, alpha quality 100, method 6, exact mode.
