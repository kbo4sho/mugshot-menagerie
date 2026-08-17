# Zippy Zebra v1 — prompts and provenance

## Route and reference roles

- Generation route: built-in Codex ImageGen.
- Reference image: `design/runtime/bumblebee/alpha/neutral-v1.png`, used only for finish, material, lighting, chibi proportion, and centered head-only composition.
- Zebra neutral is an original generation, not an edit of the Bumblebee.
- Blink and roar each use `design/runtime/zebra/chroma/neutral-v1.png` as their sole edit target and identity anchor.

## Neutral prompt

```text
Use case: stylized-concept
Asset type: reactive webcam animal-mask game character, neutral state source
Input images: Image 1 is a finish, materials, lighting, chibi proportion, and centered head-only composition reference only. Do not transform the bee and do not copy bee anatomy.
Scene/backdrop: perfectly flat uniform solid #00FF00 chroma-key field, edge to edge. No shadows, gradients, texture, reflections, floor plane, vignette, halo, or lighting variation in the background.
Primary request: Create an original front-facing chibi zebra head named Zippy Zebra, instantly recognizable as a zebra without a label.
Subject: head only; white-to-warm-ivory short plush fur; bold high-contrast charcoal-black zebra stripe map that is clean, graphic, bilaterally coherent, and includes a distinctive centered white forehead blaze framed by black stripes; upright rounded zebra ears with pale warm inner fur; a short centered black mohawk mane visible above the crown; long tapered pale muzzle; two tiny dark nostrils; soft peach blush; giant glossy honey-brown eyes; tiny closed friendly smile; no visible teeth. Expression is calm delighted neutral.
Style/medium: premium polished 2.5D plush-clay character render with subtle micro-fuzz, tactile molded volumes, warm studio highlights, deep glossy eyes, and the same level of finish as Image 1.
Composition/framing: exact straight-on symmetry, head centered, generous clear padding on every side, full ears and mohawk fully inside frame, face fills roughly 78% of canvas height, no cropped fur or silhouette.
Lighting/mood: gentle warm frontal studio lighting on the subject only; joyful, safe, preschool-friendly.
Constraints: preserve a simple bold stripe map suitable for later expression-state matching; stripe edges should be clean and stable; no green or greenish-cyan anywhere in the zebra; no neck, body, shoulders, hooves, tail, savanna, props, labels, text, watermark, border, cast shadow, contact shadow, reflection, floor, extra animal, or bee anatomy. The subject must be fully separated from the #00FF00 background with a crisp readable silhouette and no holes except true background outside the head.
```

ImageGen source:
`/Users/kevinbolander/.codex/generated_images/01a00bf6-904b-75e1-b231-c4077e5270cb/exec-24bc1ef5-fabe-4785-8db8-99f0c974ce43.png`

Workspace copy:
`design/runtime/zebra/chroma/neutral-v1.png`

Durable raw ImageGen source copy:
`design/runtime/zebra/audit/imagegen/neutral-v1.generated.png`

## Blink prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam animal-mask game character, blink state source
Input images: Image 1 is the sole edit target and identity anchor.
Primary request: Change only Zippy Zebra’s expression from neutral to a joyful blink. Replace the two open eyes with softly closed happy upward-curving lash arcs, with a tiny tidy dark lash flick at each outer corner. Keep the same tiny closed smile and blush.
Invariants: keep the exact same zebra identity, head silhouette, ears, mohawk, muzzle, nostrils, smile, centered white forehead blaze, every black stripe shape and position, fur texture, materials, colors, lighting, scale, position, framing, padding, and perfectly flat #00FF00 background pixel-for-pixel visually unchanged outside the two eye areas. Preserve straight-on symmetry. Do not redesign or re-render any other region.
Constraints: no open irises or pupils, no teeth, no mouth opening, no neck/body/props/text/watermark; no shadow/gradient/texture/floor in the green field; do not introduce green inside the zebra.
```

ImageGen source:
`/Users/kevinbolander/.codex/generated_images/01a00bf6-904b-75e1-b231-c4077e5270cb/exec-f7c44bc6-6481-44ce-bc8f-3c5e3cb61cbe.png`

Durable raw source copy:
`design/runtime/zebra/audit/imagegen/blink-v1.generated.png`

## Roar prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam animal-mask game character, joyful roar state source
Input images: Image 1 is the sole edit target and identity anchor.
Primary request: Change only Zippy Zebra’s expression from neutral to a joyful compact roar. Keep both giant honey-brown eyes open, but lift the brow expression slightly. Replace only the tiny closed smile with one small rounded safe O-shaped open mouth centered low on the pale muzzle; the mouth interior is warm dark brown with a small rounded coral-pink tongue visible at the bottom. No teeth, fangs, gums, or scary expression.
Invariants: keep the exact same zebra identity, head silhouette, ears, mohawk, muzzle shape, nostrils, blush, centered white forehead blaze, every black stripe shape and position, fur texture, materials, colors, lighting, scale, position, framing, padding, eye identity and highlights, and perfectly flat #00FF00 background visually unchanged outside localized eyebrow and mouth regions. Preserve straight-on symmetry. Do not redesign or re-render any other region.
Constraints: joyful preschool-safe expression; mouth compact, not a huge cavity; no neck/body/props/text/watermark; no shadow/gradient/texture/floor in the green field; do not introduce green inside the zebra.
```

ImageGen source:
`/Users/kevinbolander/.codex/generated_images/01a00bf6-904b-75e1-b231-c4077e5270cb/exec-acc384d2-29d9-42d3-afe5-d076b9c1366d.png`

Durable raw source copy:
`design/runtime/zebra/audit/imagegen/roar-v1.generated.png`

## Deterministic localization and export

- `build_localized_states.py` composites only two feathered eye islands for blink and one feathered mouth island for roar over the exact neutral.
- The generated roar did not create a meaningfully distinct brow shape, so no brow pixels are imported; this avoids needless stripe and forehead texture movement.
- Every pixel where an expression mask is zero is asserted identical to neutral.
- The chroma helper left 23 isolated one-pixel fully transparent holes enclosed by visible fur. `build_localized_states.py` repaired them deterministically from the median neighboring RGB and maximum neighboring alpha before locking the state matte.
- The deliverable chroma PNGs are the locked alpha masters composited over exact `#00FF00`; the untouched raw ImageGen sources remain under `audit/imagegen/`.
- All three alpha masters use the neutral alpha channel byte-for-byte.
- Runtime assets export at WebP quality 95, alpha quality 100, method 6, exact alpha.
- `export_and_audit.py` writes hostile-background, native-size, 380 px, and 0/25/50/75/100 premultiplied copy-plus-lighter blend proofs plus the manifest.
