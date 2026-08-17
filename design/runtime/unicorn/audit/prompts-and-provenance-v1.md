# Twinkle Unicorn v1 prompts and provenance

## Route and sources

- Built-in Codex ImageGen; no CLI/API fallback.
- Use-case taxonomy: `stylized-concept` for the original neutral; `precise-object-edit` for blink, roar, and the one targeted roar correction.
- Finish/composition reference only: `design/runtime/bumblebee/alpha/neutral-v1.png`. Bumblebee was not an edit target and no bee anatomy was reused.
- Neutral generated source: `/Users/kevinbolander/.codex/generated_images/01a00c6c-04f5-7632-a8e4-577778db3e2d/exec-3905c800-69f8-409a-98ab-ea0b02e302a4.png`.
- Blink generated source: `/Users/kevinbolander/.codex/generated_images/01a00c6c-04f5-7632-a8e4-577778db3e2d/exec-d4037c71-66da-4e9b-a74a-7ebaa1b0a389.png`.
- Initial roar generated source: `/Users/kevinbolander/.codex/generated_images/01a00c6c-04f5-7632-a8e4-577778db3e2d/exec-b3d8473e-f4f8-4e1c-aa1c-bb780e85ab5b.png`.
- Corrected roar generated source: `/Users/kevinbolander/.codex/generated_images/01a00c6c-04f5-7632-a8e4-577778db3e2d/exec-ecc9f370-28e9-419f-b929-cd7e25f4e71b.png`.
- Durable generated-source copies: `design/runtime/unicorn/audit/generated-{neutral,blink,roar}-v1.png`; the rejected first roar is retained as `generated-roar-v1-initial.png`.
- Deterministic post-processing and audit: `design/runtime/unicorn/audit/export_and_audit.py`.

## Neutral prompt

```text
Use case: stylized-concept
Asset type: reactive browser game animal face mask, neutral state source
Input images: Image 1 is a finish, lighting, composition, scale, centering, eye-design, cheek, and child-safe polish reference only; do not edit it and do not copy its species anatomy.
Scene/backdrop: perfectly flat solid exact #00FF00 chroma-key background for local removal. The background must be one uniform RGB color with no shadow, gradient, texture, floor plane, reflection, glow, vignette, or lighting variation.
Primary request: create one original front-facing chibi unicorn head called Twinkle Unicorn, shown as head only.
Subject: unmistakable pearl-white to very light lavender equine face; upright symmetrical horse ears; exactly one centered short spiraled horn, fully visible, with gentle gold-to-pastel coloring; a soft pastel rainbow forelock and mane framing the crown and both cheeks; elongated but compact pale muzzle; two small nostrils; subtle rosy blush; two enormous symmetrical honey-brown glossy eyes with warm highlights; gentle tiny closed smile, no visible teeth.
Style/medium: premium 2.5D plush-clay character render with subtle micro-fuzz, softly modeled volume, polished toy-like finish, friendly safe preschool appeal, matching Image 1's finish quality.
Composition/framing: centered straight-on face, nearly symmetrical; full horn and both ear tips visible with generous padding; full mane silhouette visible; face covers most of a square canvas and provides opaque canonical face coverage, while retaining at least roughly 7% clear padding around outermost horn/ear/mane silhouette; no cropped anatomy.
Lighting/mood: cheerful soft studio illumination on the subject only; warm, joyful, gentle.
Color palette: pearl white, pale lavender, honey brown, rosy peach, and a restrained soft pastel rainbow mane; do not use #00FF00 or near-chroma green anywhere in the subject.
Materials/textures: continuous opaque plush-clay surface with fine micro-fuzz; clean crisp antialiased outline; no translucent hair or wisps.
Constraints: one unicorn head only; exact flat #00FF00 background; head only; one horn only; two ears; two eyes; no neck or body; no wings; no clouds; no stars; no props; no labels; no text; no logo; no watermark; no cast/contact shadow; no floor; no reflection; no green spill; no open mouth; no tongue; no teeth.
Avoid: horse without horn, alicorn, deer anatomy, long neck, human face, asymmetry, extra horns, extra ears, cropped horn, thin transparent mane strands, busy rainbow saturation, scene elements.
```

## Blink prompt

```text
Use case: precise-object-edit
Asset type: reactive browser game animal face mask, bilateral blink state source
Input images: Image 1 is the sole edit target and sole identity source.
Primary request: change only both open eyes into matching bilateral happy closed-eye arcs and make the eyebrows subtly lift with cheerful energy. Keep the tiny closed smile neutral and closed.
Scene/backdrop: preserve the exact perfectly flat solid #00FF00 chroma-key background pixel-character and uniformity.
Subject/style: preserve this exact Twinkle Unicorn identity and premium 2.5D plush-clay micro-fuzz rendering.
Constraints: change only compact regions around the two eyes and eyebrows; both eyes must be completely closed as smooth happy arcs, with no iris, pupil, or sclera remaining; keep the horn, ears, face proportions, muzzle, nostrils, smile, blush, mane geometry and every rainbow hair lock, colors, lighting, camera, centering, silhouette, padding, and flat chroma background unchanged; no open mouth; no teeth; no tongue; no new anatomy; no text; no watermark.
Avoid: wink, one eye open, asymmetric eyelids, squint with visible eyeballs, changed mane, changed horn, changed crop, changed expression outside eyes/brows, green spill.
```

## Roar prompt

```text
Use case: precise-object-edit
Asset type: reactive browser game animal face mask, joyful roar state source
Input images: Image 1 is the sole edit target and sole identity source.
Primary request: change only the tiny closed smile into one compact joyful rounded O-shaped open mouth centered low on the pale muzzle, and lift both eyebrows slightly with delighted energy. Keep both enormous honey-brown eyes fully open and identical to Image 1.
Scene/backdrop: preserve the exact perfectly flat solid #00FF00 chroma-key background pixel-character and uniformity.
Subject/style: preserve this exact Twinkle Unicorn identity and premium 2.5D plush-clay micro-fuzz rendering.
Mouth specification: a single modest oval O cavity with a smooth continuous warm dark plum-brown interior, child-safe and uniform; no internal separation, no visible tongue, no visible teeth, no fangs, no split smile beneath it; mouth must remain compact enough to sit entirely on the pale muzzle without touching nostrils or muzzle perimeter.
Constraints: change only a compact mouth region and both eyebrow regions; preserve the horn, ears, giant open eyes, face proportions, muzzle geometry, nostrils, blush, mane geometry and every rainbow hair lock, colors, lighting, camera, centering, silhouette, padding, and flat chroma background unchanged; no body; no neck; no extra anatomy; no text; no watermark.
Avoid: huge scream, toothy grin, tongue, teeth, fangs, two mouths, smile line plus O mouth, asymmetry, altered eye identity, changed mane, changed horn, changed crop, green spill.
```

## Targeted roar correction prompt

```text
Use case: precise-object-edit
Asset type: reactive browser game animal face mask, corrected joyful roar source
Input images: Image 1 is the sole edit target.
Primary request: change only the interior of the small central O-shaped mouth. Remove the lighter pink patch at the bottom so the entire visible mouth cavity reads as one continuous uniform warm dark plum-brown interior with only subtle natural cavity shading, absolutely no tongue and no teeth.
Exact invariants: preserve the exact outer mouth shape and size, muzzle, nostrils, open eyes, lifted eyebrows, blush, horn, ears, every rainbow mane lock, face identity, materials, lighting, scale, centering, silhouette, padding, and exact perfectly flat solid #00FF00 background from Image 1. Do not change any pixel-region beyond the mouth interior.
Constraints: one mouth only; no tongue; no teeth; no fangs; no split line; no text; no watermark; no background change; no silhouette or texture drift.
```

## Deterministic processing

- Local extraction uses the installed ImageGen `remove_chroma_key.py` helper with border auto-keying, soft matte, thresholds 12/220, and despill.
- The generated field sampled as `#03FA03`; the final chroma masters are deterministically recomposited on exact `#00FF00`, with the manifest confirming every fully transparent exterior pixel is exact `#00FF00` in all three states.
- The source is uniformly scaled to 92% after extraction to create safe horn/ear/mane clearance on the original 1254-square canvas.
- The pastel mint crown lock was close enough to the key hue that the helper partially desaturated 1,636 interior subject pixels. `mint-matte-repair-mask-v1.png` records the compact crown-only repair that restores those already-detected subject pixels from the raw neutral; it does not expand the outer silhouette.
- Blink is localized to two eye islands plus two eyebrow islands. Roar is localized to one compact mouth island plus two eyebrow islands. Every pixel outside those expression masks comes from neutral.
- The one corrected ImageGen roar still retained a subtle brighter lower lobe inside the cavity. `roar-cavity-normalization-mask-v1.png` records a deterministic normalization of only already-dark cavity pixels to one continuous dark plum gradient, eliminating any tongue-like reading while preserving the rendered lip edge.
- All states receive the exact same neutral alpha plane. Native and decoded runtime alpha hashes match across states.
- WebPs are native 1254 square, quality 95, alpha quality 100, method 6, exact alpha. Public and GitHub Pages copies are byte-identical.

## Final metrics and evidence

- Shared alpha bbox: `[125, 91, 1138, 1149]`; canvas coverage: `80.78% × 84.37%`; padding: `125 / 91 / 116 / 105 px` left/top/right/bottom.
- Shared alpha hash: `761453d5d3418287fd8bba515c4b435443163ac5cc8a3c57624dd9d906ca1dd8`.
- Corner alpha is zero in all corners; visible enclosed holes at alpha threshold 32: zero.
- Conservative green-dominant partial-alpha count is 694, concentrated in legitimate pastel-mint subject edges; inspect `horn-mane-matte-closeups-v1.png` and `hostile-380-states-v1.png` for the actual light/dark/green/magenta/cyan/checker result.
- State-localized visible changes: blink `137,407 px` (`17.84%`), bbox `[279, 528, 971, 895]`; roar `44,916 px` (`5.83%`), bbox `[321, 528, 933, 1065]`.
- Runtime sizes: neutral `289,976 B`; blink `276,226 B`; roar `287,468 B`.
- Review evidence: `native-states-v1.jpg`, `states-380-and-96-v1.png`, `hostile-380-states-v1.png`, `horn-mane-matte-closeups-v1.png`, `mouth-semantics-native-and-96-v1.png`, and `copy-lighter-crossfades-380-v1.png`.
