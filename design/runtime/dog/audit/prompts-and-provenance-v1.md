# Party-Pup Dog v1 prompts and provenance

## Route and reference roles

- Generation route: built-in Codex ImageGen.
- `design/runtime/bumblebee/chroma/neutral-v1.png`: finish, lighting, material, eye-scale, padding, and centered-composition reference for the original neutral generation only. It was not an edit target.
- `design/runtime/dog/chroma/neutral-v1.png`: sole edit target and sole identity source for both expression generations.
- Chroma sources are preserved unmodified under `design/runtime/dog/chroma/`.
- Locally extracted candidates are preserved under `design/runtime/dog/audit/*-extracted-v1.png`.
- Final alpha states use neutral's exact alpha in every state and ImageGen pixels only inside feathered eye, mouth, and eyebrow regions.

## Neutral prompt

```text
Use case: stylized-concept
Asset type: reactive webcam game animal mask, neutral state source
Primary request: Create an original front-facing chibi golden-tan puppy head called Party-Pup Dog. Image 1 is a finish, lighting, material, eye-scale, padding, and centered-composition reference only; do not copy its bee anatomy or design.
Scene/backdrop: perfectly flat, exact, uniform solid #00FF00 chroma-key background, edge to edge, with no shadows, gradients, texture, reflections, floor plane, glow, or lighting variation.
Subject: unmistakably friendly puppy head only; warm golden-tan coat; long soft floppy ears; creamy muzzle and small creamy eyebrow patches; compact dark brown-black dog nose; subtle cream forehead blaze with a tiny soft tuft; rosy blush; enormous glossy honey-brown eyes with layered irises and bright highlights; neutral closed gentle smile with no visible teeth.
Style/medium: premium 2.5D plush-clay character render with delicate dense micro-fuzz and softly sculpted volume, matching Image 1's polished tactile finish and joyful child-safe quality.
Composition/framing: single symmetrical head, straight-on, centered, generous even padding, complete ears and fur silhouette fully inside frame; mask-ready face filling roughly 74–80% of square canvas; no neck or body.
Lighting/mood: warm soft frontal studio lighting contained entirely on the subject; playful, sweet, safe, immediate.
Constraints: distinctly dog/puppy, never fox, cat, bear, lion, or wolf; two long floppy ears; no pointed upright ears; no collar, body, neck, shoulders, paws, bone, bow, hat, costume, toy, or props; no open mouth; no tongue; no teeth or fangs; no text, logo, or watermark; do not use #00FF00 or near-chroma green anywhere in the subject; no cast shadow, contact shadow, reflection, halo, green glow, or green spill; crisp separable fur silhouette despite micro-fuzz.
Avoid: asymmetry, cropped ears, floor, shadow, extra appendages, accessories, photoreal dog portrait, flat vector art.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c07-582e-7bf1-9a03-445ecc9163a7/exec-e2b60514-b80c-4489-8c96-42d8d6a54190.png`

## Blink prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal mask, blink state source
Input images: Image 1 is the sole edit target and sole identity source.
Primary request: Change only the puppy's expression into a joyful full blink. Replace both open eyes with fully closed, gently upward-curving happy eyelids and short soft dark lashes. Keep the same small closed gentle smile, closed mouth, nose, brows, blush, fur, head, long floppy ears, silhouette, scale, lighting, composition, and padding exactly recognizable from Image 1.
Scene/backdrop: preserve the exact flat chroma-green backdrop of Image 1.
Style/medium: preserve the identical premium 2.5D plush-clay micro-fuzz finish.
Constraints: expression edit only, localized to the eye region; both eyes completely closed and symmetrical; no visible pupils, irises, or eye whites; no open mouth, tongue, teeth, or fangs; do not redesign, crop, rotate, rescale, recolor, relight, or retexture the puppy; no collar, body, neck, paws, props, text, logo, or watermark; no shadow, halo, green spill, or new background variation.
Avoid: wink, sleepy droop, open eye remnants, anatomy drift, ear drift, muzzle drift, fur drift, silhouette drift.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c07-582e-7bf1-9a03-445ecc9163a7/exec-7f4d9bce-bb0e-4b84-a3c9-38891f3a9fea.png`

## Roar prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal mask, roar state source
Input images: Image 1 is the sole edit target and sole identity source.
Primary request: Change only the puppy's facial expression into a delightful safe puppy roar: add a small compact rounded O-shaped open mouth centered beneath the nose, with a soft dark mouth interior and a small rounded pink tongue visible low inside; lift the creamy eyebrow patches slightly for excited surprise. Keep both enormous honey-brown eyes open, glossy, and recognizable. Preserve the exact nose, blush, muzzle, fur, head, tuft, long floppy ears, silhouette, scale, lighting, composition, and padding from Image 1.
Scene/backdrop: preserve the exact flat chroma-green backdrop of Image 1.
Style/medium: preserve the identical premium 2.5D plush-clay micro-fuzz finish.
Constraints: expression edit only, localized to the mouth and brow regions; one small child-safe O mouth; tongue is compact and fully inside the mouth; absolutely no teeth, fangs, gums, drool, growl, or aggression; distinctly delighted puppy; do not redesign, crop, rotate, rescale, recolor, relight, or retexture; no collar, body, neck, paws, props, text, logo, or watermark; no shadow, halo, green spill, or new background variation.
Avoid: huge gaping mouth, beaver teeth, cat muzzle, fox muzzle, snarling, extra tongue, open jaw wider than muzzle, identity drift, ear drift, silhouette drift, fur drift.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c07-582e-7bf1-9a03-445ecc9163a7/exec-c5b6d23f-75b2-42bb-84b6-a6ba2fa7cc20.png`

## Deterministic processing

`build_export_audit.py` localizes expression pixels, harmonizes all states to the neutral alpha, selects the largest common q94–95 export meeting the requested byte target, copies byte-identical runtime assets to both public trees, and produces the manifest plus native/96 px, hostile-background, and copy+lighter transition proof sheets.
