# Kooky Kangaroo v1 provenance

## Route and references

- Generation route: built-in Codex ImageGen.
- Approved style reference: `design/runtime/bumblebee/chroma/neutral-v1.png` (style, finish, composition, scale, padding, and lighting only).
- Initial neutral source (not selected): `/Users/kevinbolander/.codex/generated_images/01a00c7f-1ac6-7f10-ad7d-475dc1bbd062/exec-f3d6987f-13d2-4ad7-b4e2-782273c87096.png`; durable raw copy: `design/runtime/kangaroo/audit/raw/neutral-initial-generated-v1.png`.
- Selected neutral source after one targeted species correction: `/Users/kevinbolander/.codex/generated_images/01a00c7f-1ac6-7f10-ad7d-475dc1bbd062/exec-7a3533bd-ed9c-4eaa-8aff-a2e99bbad295.png`; durable raw copy: `design/runtime/kangaroo/audit/raw/neutral-generated-v1.png`.
- Blink source: `/Users/kevinbolander/.codex/generated_images/01a00c7f-1ac6-7f10-ad7d-475dc1bbd062/exec-6ab366c7-dcfd-4c6b-b27f-3ca1e4ee4389.png`; durable raw copy: `design/runtime/kangaroo/audit/raw/blink-generated-v1.png`.
- Roar-mid source: `/Users/kevinbolander/.codex/generated_images/01a00c7f-1ac6-7f10-ad7d-475dc1bbd062/exec-5866a3ec-8fde-4335-bb61-ec5b6ead7fa8.png`; durable raw copy: `design/runtime/kangaroo/audit/raw/roar-mid-generated-v1.png`.
- Roar source: `/Users/kevinbolander/.codex/generated_images/01a00c7f-1ac6-7f10-ad7d-475dc1bbd062/exec-717400e0-0a9e-4902-a403-eddec763094f.png`; durable raw copy: `design/runtime/kangaroo/audit/raw/roar-generated-v1.png`.
- Transparent sources were produced with the installed ImageGen chroma-removal helper using border auto-key, soft matte, thresholds 12/220, and despill.
- Final chroma masters were deterministically recomposited over exact `#00FF00` after alpha validation.
- Blink, roar-mid, and roar were composited only through feathered expression ROIs onto the exact selected neutral anchor. The final alpha channel is byte-identical across all four states.
- The generated roar and roar-mid cavity RGB was locally normalized to one uniform warm dark-cocoa interior, removing the generated red tongue/highlight while retaining each authored mouth silhouette.
- `roar-mid-v1.webp` is an authored semantic bridge for the existing four-state compositor. It avoids the full neutral-smile/full-roar double exposure visible in the fallback three-state blend.

## Exact prompts

### Initial neutral

```text
Use case: stylized-concept
Asset type: reactive webcam game animal face mask — neutral anchor
Input images: Image 1 is the approved Bumblebee visual style, finish, composition, scale, padding, and lighting reference only; do not preserve or copy any bee anatomy, colors, stripes, wings, antennae, or scalloped silhouette.
Primary request: Create an original front-facing chibi warm russet/tan kangaroo head as a single clean game mask asset.
Scene/backdrop: perfectly flat, exact solid #00FF00 chroma-key background for local removal. The background must be one absolutely uniform color with no shadow, gradient, texture, reflection, floor plane, halo, or lighting variation.
Subject: unmistakable kangaroo head only: warm russet and tan plush fur; very tall upright tapered kangaroo ears, fully visible and generously padded from the top edge, with pale pink inner fur; long narrow marsupial face with an elongated pale cream cheek-and-muzzle area; petite centered dark charcoal-brown nose; subtle small forehead tuft; warm coral blush; two enormous symmetrical honey-brown eyes with luminous layered irises and clean white catchlights; gently lifted brows; neutral gentle closed smile with no visible teeth. Species must read as kangaroo, not rabbit, deer, or dog, through the long narrow muzzle, wedge-shaped head, and tall tapered ear-to-head proportions.
Style/medium: premium polished 2.5D plush-clay character render matching Image 1’s tactile micro-fuzz, soft rounded forms, crisp expressive facial modeling, subtle dimensional shading, and friendly preschool-safe finish. Soft warm frontal studio lighting only on the subject.
Composition/framing: straight-on, perfectly centered and near-symmetric, generous even padding around both tall ear tips and all side fur, complete head silhouette visible, strong opaque crown and canonical full-face coverage; head-only framing with no neck or shoulders.
Color palette: warm russet, tan, pale cream, soft pink, honey-brown, coral, dark charcoal-brown; never use #00FF00 or near-key green anywhere inside the kangaroo.
Constraints: preserve the approved reference’s chibi eye-to-face proportion and production polish; kangaroo species must read instantly at 96px; no text, no watermark, no cast/contact shadow, no reflection; one head only; exact uniform #00FF00 background.
Avoid: bunny, rabbit, deer, dog, fox, wallaby ambiguity; round teddy-bear silhouette; short or floppy ears; antlers; whiskers; body; neck; pouch; paws; tail; outback scenery; foliage; ground; props; clothing; hat; fangs; teeth; open mouth; tongue; duplicate features; cropped ear tips; translucent crown; green pixels in the subject.
```

### Targeted neutral species correction

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face mask — neutral anchor targeted species correction
Input images: Image 1 is the sole edit target and identity/finish anchor.
Primary request: Correct only the species anatomy so this reads instantly as a front-facing chibi kangaroo rather than a rabbit: make the lower face subtly longer and narrower in a marsupial wedge, lengthen the central cream muzzle/bridge beneath the eyes, make the petite dark nose a little smaller and more triangular, and make both upright ears slightly narrower and more tapered with characteristic kangaroo proportions. Keep the warm russet/tan palette, huge honey-brown eyes, blush, forehead tuft, and gentle closed smile.
Constraints: preserve Image 1’s exact square composition, centered straight-on pose, premium 2.5D plush-clay micro-fuzz finish, lighting, background, scale, padding, eye identity, colors, and complete silhouette. Keep both entire ear tips safely visible. Background must remain perfectly flat exact solid #00FF00 with no gradient, shadow, texture, floor, reflection, or lighting variation. No body, neck, pouch, paws, tail, props, scenery, text, watermark, teeth, open mouth, tongue, antlers, whiskers, or extra elements. Do not turn it into a rabbit, bunny, deer, dog, fox, or mouse. Do not use #00FF00 within the subject.
```

### Blink

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face mask — blink state
Input images: Image 1 is the sole edit target and exact kangaroo identity anchor.
Primary request: Change only the eye and eyebrow expression into a delighted happy blink: both enormous eyes fully closed as smooth upward-curving dark plush lashes, with friendly slightly lifted brows. Preserve the small neutral closed smile exactly; no open mouth and no teeth.
Constraints: preserve Image 1 exactly everywhere outside the smallest eye-and-brow regions — identical 1254×1254 composition, unmistakable kangaroo identity, tall tapered ears and pink inner fur, elongated narrow marsupial head and cream muzzle, forehead tuft, russet/tan micro-fuzz, nose, blush, lighting, scale, padding, and exact flat #00FF00 chroma background. Do not redraw, move, recolor, rescale, crop, or relight anything else. Maintain premium 2.5D plush-clay finish. No new elements, text, watermark, body, neck, pouch, paws, tail, props, shadow, teeth, tongue, or open mouth. Both ear tips remain fully visible. The background stays one exact uniform #00FF00 and the subject contains no key green.
```

### Roar-mid

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face mask — authored mid-roar bridge state
Input images: Image 1 is the sole edit target and exact kangaroo identity anchor.
Primary request: Change only the mouth into the halfway expression between the neutral closed smile and the full rounded roar: a very small centered pursed circular O opening directly below the petite nose, overlapping the neutral smile’s center so it crossfades without doubled mouth shapes. Use one uniform warm dark-cocoa cavity with absolutely no tongue, teeth, fangs, highlight, split lobes, or inner shapes. Gently lift both brows halfway. Keep both enormous honey-brown eyes fully open and preserve their size, gaze, irises, and catchlights.
Constraints: preserve Image 1 exactly everywhere outside the smallest mouth-and-brow regions — identical 1254×1254 composition, unmistakable kangaroo identity, tall tapered ears and pink inner fur, elongated narrow marsupial head and cream muzzle, forehead tuft, russet/tan micro-fuzz, nose, blush, open eyes, lighting, scale, padding, and exact flat #00FF00 chroma background. Do not redraw, move, recolor, rescale, crop, or relight anything else. Maintain premium 2.5D plush-clay finish. No new elements, text, watermark, body, neck, pouch, paws, tail, props, shadow, tongue, teeth, fangs, or mouth-interior highlights. Both ear tips remain fully visible. The background stays one exact uniform #00FF00 and the subject contains no key green.
```

### Roar

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face mask — roar state
Input images: Image 1 is the sole edit target and exact kangaroo identity anchor.
Primary request: Change only the mouth and eyebrow expression into a delighted child-safe little roar: a compact centered rounded O mouth below the petite nose, with one uniform warm dark-cocoa mouth cavity and absolutely no tongue, teeth, fangs, highlights, split lobes, or inner shapes; gently lift both brows. Keep both enormous honey-brown eyes fully open and preserve their size, gaze, irises, and catchlights.
Constraints: preserve Image 1 exactly everywhere outside the smallest mouth-and-brow regions — identical 1254×1254 composition, unmistakable kangaroo identity, tall tapered ears and pink inner fur, elongated narrow marsupial head and cream muzzle, forehead tuft, russet/tan micro-fuzz, nose, blush, open eyes, lighting, scale, padding, and exact flat #00FF00 chroma background. Do not redraw, move, recolor, rescale, crop, or relight anything else. Maintain premium 2.5D plush-clay finish. No new elements, text, watermark, body, neck, pouch, paws, tail, props, shadow, tongue, teeth, fangs, or mouth-interior highlights. Both ear tips remain fully visible. The background stays one exact uniform #00FF00 and the subject contains no key green.
```

## Export and audit notes

- Runtime WebP settings: native 1254×1254, quality 95, alpha quality 100, method 6, exact alpha; 251,512–264,618 bytes for the core states and 252,968 bytes for roar-mid.
- Alpha bbox for every state: `(219, 66, 1035, 1213)`; padding: left 219, top 66, right 219, bottom 41 pixels.
- Alpha-weighted centroid for every state: `(624.661, 647.180)`; alpha coverage: `0.350955`.
- Every state has one connected alpha component, zero enclosed transparent holes, zero green-dominant partial-alpha fringe pixels, and transparent corners.
- The alpha channel is byte-identical across neutral, blink, roar-mid, and roar.
- RGB outside the authored expression localization masks is byte-identical to neutral for all derived states.
- The exterior transparent field in all chroma masters is exact `#00FF00` with zero channel delta.
- Public and GitHub Pages copies are byte-identical for all four states, and every WebP contains an `ALPH` chunk.
- Actual runtime decodes at native, 380px, 96px, hostile backgrounds, semantic four-state copy-plus-lighter crossfades, species comparison, and canonical coverage are in `design/runtime/kangaroo/audit/`.
- Independent Gauntlet approval is intentionally deferred to a separate critic.
