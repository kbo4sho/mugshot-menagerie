# Dapper Deer v1 prompts and provenance

## Route and source roles

- Generation route: built-in Codex ImageGen.
- `design/runtime/bumblebee/chroma/neutral-v1.png` was the finish, composition, lighting, eye-scale, material, and child-safe quality reference for the original neutral generation only. It was never an edit target.
- `design/runtime/deer/chroma/neutral-v1.png` was the sole edit target and identity source for both generated expression states.
- Untouched ImageGen outputs are preserved under `design/runtime/deer/audit/imagegen/`.
- Local extraction used the installed `remove_chroma_key.py` helper with border auto-key, soft matte, thresholds 12/220, and despill.
- Final blink and roar borrow only feathered expression ROIs from their generated edits. Every pixel outside those ROIs comes from the neutral master, and all three final states use the exact neutral alpha plane.
- Chroma extraction produced one isolated fully transparent pixel enclosed by visible fur; the export script repairs that one-pixel hole from neighboring subject color/alpha before the shared matte is locked.
- Final chroma masters are deterministically recomposited over exact `#00FF00`. Runtime WebPs use quality 94 or 95, alpha quality 100, method 6, exact alpha, and byte-identical copies in both public trees.

## Neutral prompt

```text
Use case: stylized-concept
Asset type: reactive webcam game animal face mask, neutral-state chroma source
Input images: Image 1 is a finish, composition, lighting, eye-scale, material, and child-safe polish reference only. Create a completely original deer; do not copy any bee anatomy, markings, antennae, wings, stripes, or silhouette.
Primary request: Create one original front-facing chibi warm fawn-brown deer head named Dapper Deer on a perfectly flat solid #00FF00 chroma-key field for local removal.
Scene/backdrop: exact uniform pure #00FF00 edge to edge, with absolutely no shadows, gradients, texture, reflections, floor plane, vignette, glow, or lighting variation.
Subject: unmistakable young deer face/head only; warm fawn-brown coat; two very large soft leaf-shaped deer ears; two small symmetrical short branching deer antlers fully visible and modest in scale, clearly deer rather than broad moose antlers; pale cream muzzle and gentle pale cream eye patches; petite dark brown-black deer nose; a few subtle small white forehead spots placed symmetrically; soft coral blush; enormous glossy honey-brown eyes with layered irises and bright catchlights; neutral tiny closed gentle smile with no visible teeth.
Style/medium: premium 2.5D plush-clay character render with controlled delicate micro-fuzz, softly sculpted volume, clean tactile materials, and the same refined child-safe quality bar as Image 1.
Composition/framing: perfectly straight-on, symmetrical, centered single head; antler tips and both ears fully inside frame; generous padding above antlers and around ears; broad opaque forehead/crown extending high enough beneath the antlers to cover a tracked human forehead; face fills roughly 74–79% of square while keeping ample crop reserve; no neck or body.
Lighting/mood: warm soft frontal studio illumination contained entirely on the subject; sweet, lively, playful, safe.
Color palette: warm cinnamon/fawn brown, pale cream, honey-brown, dark chocolate, small white spots, coral blush. Do not use #00FF00 or any near-chroma green in the subject.
Constraints: head only; exactly two ears and two small short branching antlers; antlers neither oversized nor palm-shaped; deer anatomy and petite deer nose; closed gentle smile, no open mouth, tongue, teeth, or fangs; no red nose; no body, neck, shoulders, legs, hooves, tail, forest, foliage, branches, flowers, props, hat, collar, bells, snow, text, logo, watermark, floor, cast shadow, contact shadow, reflection, halo, green spill, or chroma color inside subject; crisp removable silhouette despite micro-fuzz.
Avoid: reindeer costume, Rudolph red nose, moose, elk, cow, giraffe, goat, teddy bear, floppy dog ears, huge antlers, cropped antlers or ears, neck stump, photoreal wildlife, flat vector art, asymmetry.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c2d-a243-7320-8936-390b4ec12f90/exec-2d0eacfd-e549-441f-a444-a9c61b81de61.png`

## Blink prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal mask, blink-state chroma source
Input images: Image 1 is the sole edit target and sole identity source.
Primary request: Change only Dapper Deer's expression into a joyful full blink. Replace both enormous open eyes with fully closed, gently upward-curving happy eyelids and short soft dark lashes. Keep the same tiny closed gentle smile and closed mouth. Preserve Image 1's exact deer identity and design: warm fawn-brown head, every white forehead spot, pale cream eye patches and muzzle, petite dark nose, blush, both leaf-shaped ears, both short branching antlers, crown/forehead coverage, silhouette, scale, straight-on position, lighting, material, composition, and generous padding.
Scene/backdrop: preserve the exact perfectly flat uniform solid #00FF00 chroma-key field with no shadows, gradients, texture, floor, reflections, glow, or variation.
Style/medium: preserve the identical premium 2.5D plush-clay micro-fuzz finish.
Constraints: change only the compact eye/eyelid expression regions; both eyes fully closed and symmetric with no pupil, iris, eye white, or catchlight visible; mouth remains closed; no tongue, teeth, or fangs; do not redesign, regenerate, move, rotate, crop, rescale, recolor, relight, or retexture the deer, spots, antlers, ears, muzzle, fur, or background; no body, neck, forest, foliage, flowers, props, accessories, red nose, text, logo, watermark, floor, shadow, reflection, halo, green spill, or new background variation.
Transition requirement: this state will be crossfaded with the neutral using premultiplied copy-plus-lighter weights, so every pixel outside the smallest eye-expression islands should remain visually identical to Image 1 without fur, spot, antler, or silhouette shimmer.
Avoid: wink, sleepy droop, open-eye remnants, extra eyelashes, mouth opening, antler drift, ear drift, spot drift, muzzle drift, fur drift, reindeer or moose redesign.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c2d-a243-7320-8936-390b4ec12f90/exec-2dbc3b31-aabb-4fba-bb34-681c752e031f.png`

## Roar prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal mask, joyful roar-state chroma source
Input images: Image 1 is the sole edit target and sole identity source.
Primary request: Change only Dapper Deer's facial expression into a joyful compact child-safe deer roar. Replace the tiny closed smile with one small centered rounded O-shaped open mouth below the nose, containing a soft dark mouth cavity and a small rounded pink tongue visible low inside. Lift the brows subtly in delighted surprise while keeping both enormous glossy honey-brown eyes open and fully recognizable. Preserve Image 1's exact deer identity and design: warm fawn-brown head, every white forehead spot, pale cream eye patches and muzzle, petite dark nose, blush, both leaf-shaped ears, both short branching antlers, crown/forehead coverage, silhouette, scale, straight-on position, lighting, material, composition, and generous padding.
Scene/backdrop: preserve the exact perfectly flat uniform solid #00FF00 chroma-key field with no shadows, gradients, texture, floor, reflections, glow, or variation.
Style/medium: preserve the identical premium 2.5D plush-clay micro-fuzz finish.
Constraints: change only the smallest mouth/tongue and subtle brow expression regions; one compact rounded O mouth, much narrower than the muzzle, with tongue fully inside; absolutely no teeth, fangs, gums, drool, snarl, or aggression; eyes remain open; do not redesign, regenerate, move, rotate, crop, rescale, recolor, relight, or retexture the deer, spots, antlers, ears, muzzle, fur, or background; no body, neck, forest, foliage, flowers, props, accessories, red nose, text, logo, watermark, floor, shadow, reflection, halo, green spill, or new background variation.
Transition requirement: this state will be crossfaded with neutral using premultiplied copy-plus-lighter weights, so every pixel outside the smallest mouth and brow expression islands should remain visually identical to Image 1 without fur, spot, antler, eye, or silhouette shimmer.
Avoid: huge gaping scream, teeth, fangs, beaver mouth, human lips, second mouth, tongue outside mouth, snarling, eye redesign, antler drift, ear drift, spot drift, muzzle drift, fur drift, reindeer or moose redesign.
```

Built-in source: `/Users/kevinbolander/.codex/generated_images/01a00c2d-a243-7320-8936-390b4ec12f90/exec-19dae81c-9dfa-4150-9c95-c7341acdfbaa.png`

## Deterministic processing

`export_and_audit.py` restricts blink to two bilateral eye islands and roar to one compact mouth island plus two brow islands, applies neutral's exact alpha to all three states, rebuilds exact-green chroma masters, selects the largest common q94–95 runtime export satisfying the byte bar, copies byte-identical assets to both runtime trees, and emits review sheets plus a metrics manifest. The canonical forehead proof uses the app's 380 px tracked-face ellipse and verifies full opacity plus at least 34.8 px of crown margin for static and ±8° bounce cases.
