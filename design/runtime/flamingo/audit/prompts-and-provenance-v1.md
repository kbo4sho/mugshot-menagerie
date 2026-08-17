# Fancy Flamingo v1 — prompts and provenance

## Route and source roles

- Generation route: built-in ImageGen.
- `design/runtime/bumblebee/alpha/neutral-v1.png`: finish/composition reference only for the original neutral generation.
- `design/runtime/flamingo/chroma/neutral-raw-v1.png`: sole edit target for both expression generations.
- No Bumblebee anatomy, colors, markings, or silhouette were used as Flamingo content.
- The first roar result was rejected before asset assembly because its lower-jaw gape changed the beak silhouette too much. The one allowed targeted retry produced the source used in v1.

## Exact neutral prompt

```text
Use case: stylized-concept
Asset type: reactive webcam game character mask, neutral state master
Input images: Image 1 is a finish and composition reference only; do not copy its bee anatomy, markings, silhouette, colors, antennae, or wings
Primary request: Create an original, unmistakable Fancy Flamingo face and head only, front-facing and perfectly symmetrical enough for a reactive face mask.
Scene/backdrop: perfectly flat uniform exact solid #00FF00 chroma-key field for local removal; one single color edge-to-edge, absolutely no shadows, gradient, texture, vignette, floor plane, reflection, or lighting variation
Subject: chibi coral-pink flamingo plush-feather head; rounded feather crown with a solid opaque forehead-covering cap and a subtle small crest; slightly long narrow face tapering naturally into a characteristic flamingo beak; two-tone hooked beak with pale blush-pink upper/base section and a charcoal curved tip; soft cheek feather tufts; warm coral blush; two giant expressive honey-brown glassy eyes with warm amber irises and clean catchlights; closed friendly beak in neutral state
Style/medium: premium polished 2.5D chibi character render; softly rounded plush-clay construction with refined short feather microtexture; match Image 1 only in finish quality, tactile richness, giant-eye appeal, centered icon composition, and kid-safe charm
Composition/framing: single centered head, straight-on eye-level view, no neck; balanced bilateral silhouette; generous transparent-safe padding on all sides including above crest and below beak; face fills most of square while all feather tips and hooked beak remain far from crop; solid crown must cover tracked forehead and the face mass must cover the full human face
Lighting/mood: soft even studio-style character lighting applied only to the subject, cheerful and friendly
Color palette: flamingo coral pink, peach blush, honey-brown/amber eyes, pale pink beak base, charcoal beak tip; do not use green anywhere in subject
Materials/textures: cohesive plush feather microtexture with subtle clay-like volume; crisp readable silhouette; no translucent feathers
Constraints: Flamingo face/head only. Preserve a compact mask-ready shape. Exactly two eyes. Neutral eyes fully open. Beak completely closed and friendly. No tongue, teeth, text, symbols, logo, watermark, labels, border, frame, shadow, or ground contact. Background must remain exactly flat #00FF00 and fully separated from subject.
Avoid: neck, body, wings, legs, feet, water, reeds, nest, props, scenery, extra faces, side view, long dangling beak, photoreal bird, costume, hood, bee features, lime/green details, chroma-key green spill inside subject, floor, cast shadow, contact shadow, glow, blur, clipped details
```

## Exact blink prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam game character mask, bilateral blink state
Input images: Image 1 is the sole edit target and locked character anchor
Primary request: Change only both eyes into a happy synchronized blink: replace both open eyeballs with clean, gentle, dark closed-eye upward-curving arcs, with a small soft eyelid/cheek lift that feels delighted and kid-friendly.
State semantics: unmistakably bilateral closed blink; no visible iris, pupil, sclera, or glass eye in either eye; both eyes must be fully closed at the same time.
Constraints: Preserve the exact Fancy Flamingo identity, head silhouette, scale, position, coral feather crown and crest, cheek tufts, facial proportions, feather microtexture, colors, lighting, blush, two-tone pale-pink-and-charcoal hooked beak, closed friendly beak, and exact uniform #00FF00 background. Change only compact regions around both eyes. Keep the beak completely closed. No neck/body/wings/legs/water/props, no text, no watermark, no added elements, no crop shift, no camera shift, no restyling, no background variation.
Avoid: open eyes, winking one eye, extra eyelids, eyelashes, tears, tongue, teeth, open beak, mouth change, different crest, changed feathers, changed silhouette, green spill, shadow, floor
```

## Exact rejected roar prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam game character mask, roar/vocal state
Input images: Image 1 is the sole edit target and locked character anchor
Primary request: Change only the expression to a joyful compact flamingo vocal/roar state: keep both giant honey-brown eyes open, lift the brows slightly, and open the two-tone hooked beak into a small, safe, readable central O/open-beak shape with a warm coral mouth interior. The opening should feel like a delighted "ah!" while retaining the unmistakable flamingo pale-pink base and charcoal curved tip.
State semantics: a compact vocal opening, not aggressive; no tongue and no teeth; eyes fully open; the outer beak silhouette remains almost exactly where it is so the mask crossfade is stable.
Constraints: Preserve the exact Fancy Flamingo identity, head silhouette, scale, position, coral feather crown and crest, cheek tufts, facial proportions, feather microtexture, colors, lighting, blush, eye identity, hooked two-tone beak identity, and exact uniform #00FF00 background. Change only compact regions at the brows and center of the beak/mouth. Keep the charcoal hook prominent and connected to the pale pink beak. No neck/body/wings/legs/water/props, no text, no watermark, no crop shift, no camera shift, no restyling, no background variation.
Avoid: tongue, teeth, fangs, giant gape, detached lower jaw, duck bill, extra beak, changed eye size, closed eyes, scary snarl, side view, altered crest, changed cheek tufts, changed silhouette, green spill, shadow, floor
```

## Exact selected roar retry prompt

```text
Use case: precise-object-edit
Asset type: reactive webcam game character mask, compact roar/vocal state — targeted retry
Input images: Image 1 is the sole edit target and locked character anchor
Primary request: Change only the expression into a joyful but VERY SMALL flamingo vocal state. Add a compact warm-coral oval mouth opening directly at the central seam where the pale-pink beak base meets the charcoal hook, only about one quarter of the beak's total height. Keep the charcoal hook and entire outer beak silhouette exactly unchanged and continuous. Lift the coral feather brows subtly while both giant honey-brown eyes remain fully open.
State semantics: tiny delighted "o!", not a gape; no separated jaw; no tongue and no teeth. The beak still reads as the exact same hooked flamingo beak.
Hard invariants: Preserve pixel-level character identity outside small feathered ROIs at the two brows and central beak seam. Preserve exact head silhouette, crest, cheek tufts, scale, position, crop, feather microtexture, colors, lighting, blush, open eyes, beak exterior, and perfectly uniform #00FF00 background. No neck/body/wings/legs/water/props, text, watermark, shadow, floor, restyling, crop shift, or background variation.
Avoid: giant gape, open lower jaw, dangling jaw, split beak, beak enlargement, altered charcoal tip, tongue, teeth, fangs, aggressive roar, closed eyes, eye drift, extra elements
```

## Deterministic assembly and exports

- Neutral chroma extraction used the installed ImageGen helper with border auto-keying, soft matte, thresholds 12/220, and despill.
- Blink RGB is feather-localized to two eye regions; roar RGB is feather-localized to two brow regions and one compact central beak-seam region.
- Every localized state is assigned the exact neutral alpha plane. The perimeter and all pixels outside the expression masks are neutral pixels.
- Runtime WebPs are native 1254 square, q95, alpha quality 100, method 6, exact alpha.
- Public and GitHub Pages copies are byte-identical.

## Evidence summary

- Runtime weights: neutral 258,200 bytes; blink 270,252 bytes; roar 249,232 bytes.
- Shared alpha bbox: `(136, 74, 1119, 1180)` with padding `(136, 74, 135, 74)`.
- Shared alpha centroid: `(628.625, 645.505)`.
- Canonical face and forehead opaque coverage at 380 px: `1.0` each.
- Alpha hashes are identical across all states; four corner alpha values are zero; enclosed transparent holes: zero; green-dominant partial-alpha pixels: zero.
- Maximum channel delta outside expression localization masks: zero for blink and roar.
- Native, 380 px, 96 px, hostile-background, and current copy-plus-lighter multiweight proofs are saved beside this file.

## Builder concern for independent review

- The elongated charcoal hook is a strong species cue and is safely padded, but it adds more vertical visual weight than the round Bumblebee anchor. The independent critic should judge whether its size feels delightful and face-covering in the actual gallery/runtime scale.
- Builder has not approved the pack.
