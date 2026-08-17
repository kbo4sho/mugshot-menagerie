# Kooky Kangaroo v3 provenance

## Scope and route

- Critic-directed repair scope: replace the v2 procedural-looking jaw with authored high-quality ImageGen expression edits while preserving the accepted neutral, blink, species read, fur, matte, alpha, and canonical coverage.
- Generation route: built-in Codex ImageGen.
- Mid input/sole target: accepted neutral `/Users/kevinbolander/.codex/generated_images/01a00c7f-1ac6-7f10-ad7d-475dc1bbd062/exec-7a3533bd-ed9c-4eaa-8aff-a2e99bbad295.png`.
- Selected mid output: `/Users/kevinbolander/.codex/generated_images/01a00c7f-1ac6-7f10-ad7d-475dc1bbd062/exec-b245dc4d-bf42-459c-ba18-3d862616f8ab.png`; durable raw copy: `design/runtime/kangaroo/audit/raw/roar-mid-generated-v3.png`.
- Roar input/sole target: the selected v3 mid output above.
- Roar output: `/Users/kevinbolander/.codex/generated_images/01a00c7f-1ac6-7f10-ad7d-475dc1bbd062/exec-fe6404bb-30cf-4c96-a491-148c8a6c28f2.png`; durable raw copy: `design/runtime/kangaroo/audit/raw/roar-generated-v3.png`.
- The generated roar globally redrew the face, so those drifted global pixels were rejected. Only its authored lower-mouth expression pixels were aligned beneath the selected mid’s exact upper rim. Final identity comes entirely from the accepted neutral/mid, with RGB delta exactly zero outside the jaw ROI.
- ImageGen introduced red tongue color in both cavity sources. The generated mouth geometry, dimensional fur lips, and transitions are retained, while the interior is tone-normalized to one uniform warm dark cocoa `(58, 22, 18)` as required.
- V1 and v2 source, master, and runtime files are preserved checksum-identically.

## Exact prompts

### V3 natural mid-roar

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face mask — v3 natural mid-roar
Input images: Image 1 is the sole edit target and exact approved kangaroo identity anchor.
Primary request: Edit ONLY the existing smile/philtrum region into one natural, shallow, half-open marsupial mouth. The exact old U-smile position becomes the soft dimensional UPPER LIP/RIM of the new opening. Replace the complete old side-smile arcs and the entire dark vertical philtrum below the nose; the cream plush fur between nose and upper lip must be clean and uninterrupted, with NO line, seam, stem, or connector. Directly under that upper lip, show one shallow gently curved horizontal opening with a uniform warm dark-cocoa cavity and a soft sampled cream-fur lower lip. It should look like a real plush-clay jaw beginning to open, not a graphic symbol.
Critical topology: one contiguous horizontal mouth only; no detached lower oval, no round O, no lollipop, no exclamation mark, no hard-cut rectangular tabs, no moustache, no leftover smile arcs, no black cartoon outline. The cavity is shallow and dimensional, not flat. No tongue, teeth, fangs, highlights, lighter lower lobe, inner ring, or second shape.
Constraints: preserve Image 1 exactly everywhere outside the smallest mouth-and-philtrum edit region — identical 1254×1254 composition, kangaroo identity, head/ear silhouette, eye size/gaze/irises/catchlights, brows, petite nose, cream muzzle markings, russet/tan plush micro-fuzz, blush, lighting, scale, padding, and exact flat #00FF00 background. Do not change the nose itself. No identity drift, redraw, rescale, crop, relight, text, watermark, body, props, or shadow. Background remains perfectly uniform #00FF00; subject contains no key green.
```

### V3 natural full roar

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face mask — v3 natural full roar
Input images: Image 1 is the sole edit target and exact selected v3 mid-roar identity and mouth-topology anchor.
Primary request: Expand ONLY the LOWER HALF of Image 1’s existing shallow mouth cavity downward into one naturally open delighted marsupial roar. Preserve the existing upper lip/rim, left and right mouth corners, horizontal width, position, curvature, cream sampled-fur texture, and fur-to-lip transition exactly. The same cavity simply opens farther downward; do not move it upward, make it wider, or redesign the upper rim. Preserve the clean uninterrupted cream fur between nose and upper lip with no philtrum or connector. Make the interior one uniform warm dark-cocoa cavity and the lower lip a soft dimensional sampled-fur edge.
Critical topology: one contiguous naturally enlarged mouth only; no detached O, no lower lobe, no inner oval, no lighter bottom section, no nested ring, no doubled outline, no stem, no lollipop, no exclamation mark, no smile arcs, no hard-cut tabs, no black cartoon outline. No tongue, teeth, fangs, highlights, inner shapes, or color split.
Constraints: preserve Image 1 exactly everywhere outside the smallest lower-mouth expansion region — identical 1254×1254 composition, kangaroo identity, head/ear silhouette, eyes, gaze, irises, catchlights, brows, petite nose, cream muzzle markings, russet/tan plush micro-fuzz, blush, lighting, scale, padding, and exact flat #00FF00 background. Do not alter the nose or upper lip. No identity drift, redraw, rescale, crop, relight, text, watermark, body, props, or shadow. Background remains perfectly uniform #00FF00; subject contains no key green.
```

## Final localization and invariants

- `roar-mid-v3` localizes the selected generated mouth and the immediately surrounding sampled fur through a feathered lower-muzzle mask onto the exact accepted neutral.
- The neutral nose is protected from the edit. The generated clean cream-fur bridge removes the old side-smile and philtrum in the same localized transition.
- The full-roar generated mouth crop is aligned to the selected mid’s coordinate system. Only its lower expansion is composited, through a soft vertical ramp beginning below the selected mid’s upper rim; the final roar therefore retains that exact upper rim, corners, and material.
- Final cavity tone normalization changes color only inside the generated mouth interiors; it does not author or redraw the cavity silhouette.
- Both expression states are composited back over the exact neutral outside native jaw ROI `(510, 1080, 740, 1212)`, making outside-ROI RGB delta zero.
- All four v3 states use the exact accepted v1 neutral alpha matte.

## Export and audit evidence

- Runtime WebPs: native 1254×1254, quality 95, alpha quality 100, method 6, exact alpha.
- Runtime sizes: neutral 257,558 bytes; blink 264,618 bytes; roar-mid 255,972 bytes; roar 254,496 bytes.
- Actual public v3 WebPs are decoded and passed through the exact four-state helper at jaw values `0`, `.125`, `.25`, `.375`, `.5`, `.625`, `.75`, `.875`, and `1`.
- Visual evidence is authoritative: `design/runtime/kangaroo/audit/helper-jaw-sweep-380-v3.png` and `design/runtime/kangaroo/audit/helper-jaw-sweep-96-v3.png`.
- The sweep shows the neutral smile and philtrum fading together into one shallow authored mouth, followed by downward expansion from the same upper rim. There is no detached O, lollipop/exclamation midpoint, hard-cut tab, nested ring, lighter lower lobe, or split cavity.
- State review: `design/runtime/kangaroo/audit/states-380-and-96-v3.png`.
- Hostile matte review: `design/runtime/kangaroo/audit/hostile-380-states-v3.png`.
- Metrics and exact source/output hashes: `design/runtime/kangaroo/manifest-v3.json`.
- Alpha is byte-identical across all four v3 states; bbox/padding remain `(219, 66, 1035, 1213)` / `(219, 66, 219, 41)`; one alpha component, zero enclosed holes, zero green-dominant partial-alpha fringe, exact `#00FF00` chroma exterior.
- Public and GitHub Pages v3 files are byte-identical and every runtime WebP contains `ALPH`.
- Independent Gauntlet approval is intentionally deferred to a fresh critic.
