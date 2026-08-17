# Silly Shark v1 provenance

## Route and sources

- Generation route: built-in ImageGen.
- Neutral style/composition reference only: `design/runtime/bumblebee/alpha/neutral-v1.png`.
- Blink edit target and sole source: generated Shark neutral.
- Roar edit target and sole source: generated Shark neutral.
- Generated chroma sources are archived as `design/runtime/shark/audit/{state}-generated-v1.png`.
- Final localized chroma masters: `design/runtime/shark/chroma/{state}-v1.png`.
- Final shared-alpha masters: `design/runtime/shark/alpha/{state}-v1.png`.
- Runtime exports: `public/masks/shark/{state}-v1.webp` plus byte-identical GitHub Pages copies.

## Neutral prompt

```text
Use case: stylized-concept
Asset type: Giggle Zoo real-time reactive face-mask game asset, neutral state source
Primary request: Generate a brand-new original front-facing chibi Silly Shark head/face-mask on an exact perfectly flat solid #00FF00 chroma-key field. Image 1 is a style, finish, scale, centering, eye design, cheek, and padding reference only; do not edit it, copy its anatomy, or include bee features.
Scene/backdrop: one completely uniform edge-to-edge #00FF00 background for clean removal, with no gradient, texture, shadow, floor, horizon, reflection, glow, vignette, or lighting variation.
Subject: one unmistakable unlabeled blue-gray shark head only, facing straight forward and centered. Broad streamlined domed crown, short blunt shark snout, pale cool-cream underside/muzzle area, three tiny curved gill slits on each side contained inside the head silhouette, and one small centered dorsal-fin-like crown cue fully attached to the top silhouette. No neck or torso. Make the shark silhouette distinct from dolphin, whale, generic fish, or seal. Giant glossy honey-brown eyes with warm amber irises, dark pupils, oversized white highlights, soft raised blue-gray brows, peach-coral cheek blush, tiny nostrils, and a gentle closed curved smile. Absolutely no teeth in this neutral state.
Style/medium: premium highly polished 2.5D chibi plush-clay character render matching Image 1's delightful quality bar: rounded toy-like volumes, soft fine skin/fuzz microtexture, subtle handcrafted surface, clean controlled highlights, crisp readable silhouette, rich but child-safe color, no photorealism.
Composition/framing: square canvas, head fills about 78–82% of both width and height, visually centered slightly above midline, generous transparent-export padding on every side, entire crown cue and cheeks comfortably in frame. Face should cover a webcam face well; eyes high-middle, muzzle and smile low-middle. Symmetric near-front view.
Lighting/mood: cheerful soft studio-style light on the subject only, joyful, silly, cuddly, safe for young children.
Color palette: blue-gray crown and sides, slightly deeper blue rim/side shading, pale cool-cream muzzle/underside, honey-brown eyes, coral blush. Do not use #00FF00 or any green hue anywhere in the subject.
Constraints: exactly one shark head; neutral gentle closed smile; zero visible teeth; gills remain subtle and inside the head; dorsal cue stays fully attached; opaque crown/forehead coverage; no labels, letters, watermark, logos, props, water, bubbles, seascape, body, neck, tail, separate pectoral fins, extra floating fins, hands, clothing, accessories, floor, cast/contact shadow, reflection, or detached pieces. Keep the chroma field perfectly uniform #00FF00 all the way to the subject edge. Crisp antialiased edges and generous padding.
Avoid: scary shark, rows of teeth, fangs, open mouth, aggressive expression, dolphin beak, whale blowhole, fish body, realistic wet skin, glossy plastic, extra eyes, asymmetry, cropped silhouette, low-resolution texture.
```

## Blink prompt

```text
Use case: precise-object-edit
Asset type: Giggle Zoo reactive face-mask game asset, BLINK source
Input images: Image 1 is the sole edit target and identity master.
Primary request: Edit only the expression of the exact shark in Image 1 into a happy blink. Replace the two open glossy eyes with two clean, thick, softly curved closed-eye arcs in the same eye locations. Lift the brows slightly into cheerful matching arcs. Keep the same gentle closed smile and no teeth.
Invariants: preserve the exact same shark identity, blue-gray and cream colors, head silhouette, dorsal crown cue, proportions, placement, crop, padding, gill slits, nose, cheeks, blush, muzzle, fine plush-clay skin texture, lighting, and exact perfectly flat #00FF00 background. Change only the eye interior/eyelid region and the brows. The two closed lids must feel sculpted and premium, symmetrical, friendly, and readable at 96px.
Constraints: zero visible teeth; mouth stays closed; no body, neck, tail, fins, water, bubbles, props, text, logo, watermark, shadow, floor, reflection, or added elements. Do not add eyelashes. Keep all of the shark fully inside frame. Do not use green anywhere in the subject. Background must remain one uniform edge-to-edge exact #00FF00 chroma field with no lighting variation.
Avoid: asymmetry, sleepy sadness, winking one eye, scary expression, open mouth, image-wide restyling, altered gills, altered silhouette, changed skin texture, changed camera, changed crop.
```

## Roar prompt

```text
Use case: precise-object-edit
Asset type: Giggle Zoo reactive face-mask game asset, ROAR source
Input images: Image 1 is the sole edit target and identity master.
Primary request: Edit only the expression of the exact shark in Image 1 into a joyful child-safe little roar. Change the closed smile into one compact vertical rounded O-shaped open mouth centered in the same lower-muzzle area, with a warm coral tongue visible at the bottom and exactly TWO tiny rounded blunt cartoon upper teeth total, one near each upper corner. The teeth must be small, soft, widely separated, and cute—never a row, never pointed or scary. Lift the brows slightly; keep the giant honey-brown eyes open, recognizable, and delighted.
Invariants: preserve the exact same shark identity, blue-gray and cream colors, eye design and locations, head silhouette, dorsal crown cue, proportions, placement, crop, padding, gill slits, nose, cheeks, blush, muzzle boundary, fine plush-clay skin texture, lighting, and exact perfectly flat #00FF00 background. Change only the compact mouth region and a small brow-expression region. The open mouth must remain fully inside the cream muzzle and read clearly at 96px.
Constraints: exactly two tiny rounded blunt teeth maximum; compact O mouth, not a wide jaw; no rows of teeth, no fangs, no gums, no aggressive snarl. No body, neck, tail, fins, water, bubbles, props, text, logo, watermark, shadow, floor, reflection, or added elements. Do not use green anywhere in the subject. Background must remain one uniform edge-to-edge exact #00FF00 chroma field with no lighting variation.
Avoid: scary shark, toothy grin, triangular serrated teeth, more than two teeth, huge mouth, split muzzle, altered eye identity, image-wide restyling, altered gills, altered silhouette, changed skin texture, changed camera, changed crop, asymmetry.
```
