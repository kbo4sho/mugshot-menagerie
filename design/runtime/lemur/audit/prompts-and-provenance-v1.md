# Loopy Lemur v1 prompts and provenance

## Route

- Generation: built-in ImageGen.
- Bumblebee v1 neutral was supplied only as a finish, material, lighting, and centered-composition reference.
- The generated lemur neutral was the sole edit target for blink and roar.
- The installed chroma-removal helper extracts the neutral silhouette. Expression RGB is localized, and every final state receives the neutral alpha plane.
- A deterministic `roar-mid` bridge compresses the localized final-roar mouth region over the neutral and carries the lifted brows; no additional generated source is used.
- ImageGen rendered the requested green field within a few RGB values (`#03f905` at the sampled border); the durable chroma masters are deterministically rekeyed to exact `#00ff00` at every transparent-background pixel and all four corners.

## Neutral prompt

```text
Use case: stylized-concept
Asset type: reactive webcam game animal mask, neutral state source
Input images: Image 1 is a style, finish, lighting, and centered composition reference only; do not copy the bee's anatomy, colors, antennae, stripes, wings, or silhouette.
Primary request: Create one original front-facing chibi ring-tailed lemur HEAD ONLY on a perfectly flat solid #00FF00 chroma-key background for later background removal.
Subject: an unmistakable friendly ring-tailed lemur with a compact silver-gray plush head; large rounded ears with thick white outer ruffs and soft gray inner ears; bold white facial ruff wrapping the cheeks and forehead; charcoal-black symmetrical eye-mask patches; very large round amber/honey eyes with glossy catchlights; a clearly projecting long narrow pale-gray muzzle; tiny black nose; subtle crown tuft; warm peach blush; tiny gentle closed smile with no visible teeth. Lemur proportions must be distinct from raccoon, panda, or monkey: huge orange eyes, narrow long muzzle, white ear ruffs, delicate crown.
Style/medium: premium 2.5D plush-clay character render, tactile soft microfiber/felt surface, polished family-animation quality, matching Image 1's dimensional softness and premium toy-like finish.
Composition/framing: centered, perfectly front-facing and bilaterally symmetrical, head fills about 82% of the square canvas, ears and crown fully visible, generous even padding on all four sides, opaque face suitable for covering a human face. No neck or body.
Lighting/mood: soft frontal studio lighting contained entirely on the subject, joyful and safe for young children.
Scene/backdrop: the background must be one perfectly uniform exact #00FF00 field with no shadows, gradient, texture, reflections, floor plane, halo, glow, or lighting variation.
Constraints: use no #00FF00 within the character; crisp clean silhouette; no cast shadow; no contact shadow; no text; no watermark; no label; no props; no branch; no tail; no body; no teeth; no tongue; no open mouth. Exactly one face, two ears, two open eyes, one nose.
Avoid: raccoon, panda, monkey, bear, mask costume, tail, stripes, antennae, wings, accessories, asymmetrical three-quarter view, cropped ears, green spill, transparent or semi-transparent facial areas.
```

## Blink prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal mask, BLINK state source
Input images: Image 1 is the edit target and approved neutral Loopy Lemur identity.
Primary request: Change only the eye and eyebrow expression into a clear bilateral blink. Close both amber eyes completely into matching soft upward happy arcs with plush charcoal eyelids; keep the brow area relaxed and sweet.
Invariants: preserve the exact same ring-tailed lemur identity, head silhouette, centered front-facing pose, scale, ears, white ear ruffs, crown tuft, white facial ruff, charcoal mask patches, long narrow pale muzzle, black nose, cheeks, blush, tiny closed smile, materials, lighting, and exact pixel composition. Keep the mouth closed and unchanged. Keep the background perfectly uniform exact #00FF00 with no gradients, shadows, texture, halo, or spill.
Constraints: exactly two closed eyes; no visible eyeballs; no body; no tail; no branch; no props; no text; no watermark; no teeth; no tongue; crisp isolated subject; no green inside subject.
```

## Roar prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal mask, ROAR state source
Input images: Image 1 is the edit target and approved neutral Loopy Lemur identity.
Primary request: Change only the brows and lower muzzle/mouth expression into a kid-safe excited roar. Keep both giant amber/honey eyes fully open and recognizable; lift both brows gently. Replace the tiny smile with one compact, perfectly centered, uniform oval O-shaped open mouth cavity under the black nose. The cavity should be dark warm charcoal, small-to-medium, smooth, clean, and fully enclosed inside the pale muzzle, with no tongue, no teeth, no split, no duplicated mouth, and no detached lower jaw.
Invariants: preserve the exact same ring-tailed lemur identity, head silhouette, centered front-facing pose, scale, ears, white ear ruffs, crown tuft, white facial ruff, charcoal mask patches, long narrow pale muzzle, black nose, cheeks, blush, eye size/color/catchlights, materials, lighting, and exact pixel composition. Keep the background perfectly uniform exact #00FF00 with no gradients, shadows, texture, halo, or spill.
Constraints: one face, one nose, one mouth cavity; no body; no tail; no branch; no props; no text; no watermark; no teeth; no tongue; crisp isolated subject; no green inside subject.
```

## Deterministic export contract

- Durable generated sources: `design/runtime/lemur/audit/generated-{neutral,blink,roar}-v1.png`
- Localized chroma masters: `design/runtime/lemur/chroma/{neutral,blink,roar-mid,roar}-v1.png`
- Shared-alpha masters: `design/runtime/lemur/alpha/{neutral,blink,roar-mid,roar}-v1.png`
- Runtime: `public/masks/lemur/{neutral,blink,roar-mid,roar}-v1.webp`
- GitHub Pages mirror: `github-pages/public/masks/lemur/{neutral,blink,roar-mid,roar}-v1.webp`
- Metrics, checksums, exact runtime dimensions/quality, and audit evidence: `manifest-v1.json`
