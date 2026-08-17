# Kooky Kangaroo v2 provenance

## Scope and route

- Critic-directed repair scope: jaw topology only. The approved v1 species read, finish, matte, alpha, canonical coverage, neutral, and blink are preserved.
- Generation route: built-in Codex ImageGen for the authored shallow-mouth source; deterministic local compositing for exact compatible mid/full topology.
- Neutral source: exact v1 neutral pixels from `design/runtime/kangaroo/alpha/neutral-v1.png`.
- Blink source: exact v1 blink pixels from `design/runtime/kangaroo/alpha/blink-v1.png`.
- Selected v2 mid-mouth ImageGen source: `/Users/kevinbolander/.codex/generated_images/01a00c7f-1ac6-7f10-ad7d-475dc1bbd062/exec-24ca4b1c-4d42-447b-959c-4d471ef42a86.png`; durable raw copy: `design/runtime/kangaroo/audit/raw/roar-mid-generated-v2.png`.
- First v2 full-roar ImageGen attempt (rejected for incompatible width/topology): `/Users/kevinbolander/.codex/generated_images/01a00c7f-1ac6-7f10-ad7d-475dc1bbd062/exec-1a2f15f3-54ec-4b42-8d74-ce00dbb496ac.png`; durable raw copy: `design/runtime/kangaroo/audit/raw/roar-initial-generated-v2.png`.
- Targeted full-roar retry from the mid source (rejected for detached O/connector topology): `/Users/kevinbolander/.codex/generated_images/01a00c7f-1ac6-7f10-ad7d-475dc1bbd062/exec-54d433bf-c186-4c0f-bd66-7dae6314575a.png`; durable raw copy: `design/runtime/kangaroo/audit/raw/roar-generated-v2.png`.
- Final `roar-mid-v2` localizes only the selected shallow mouth onto the v1 neutral, removes the vertical nose-to-mouth connector with horizontally sampled muzzle fur, and normalizes the cavity to uniform warm dark cocoa.
- Final `roar-v2` starts from that exact final mid image and extends only the lower cavity downward. The upper rim, corners, position, width, material, and cavity color are therefore identical by construction.
- All changes are hard-bounded to native jaw ROI `(510, 1080, 740, 1212)`; RGB delta outside it is exactly zero.
- All four v2 states use the byte-identical v1 neutral alpha matte.

## Exact prompts

### V2 authored mid-roar

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face mask — v2 authored mid-roar bridge
Input images: Image 1 is the sole edit target and exact approved kangaroo identity anchor.
Primary request: Redesign only the mouth and the tiny fur area immediately between mouth and nose so this is a natural halfway-open jaw that begins on the exact existing neutral U-smile curve. Replace the entire neutral smile drawing and vertical philtrum below the nose with ONE contiguous shallow horizontal oval/crescent opening spanning the former smile from side to side. The opening must have a dimensional sampled-fur upper lip rim that follows the former smile curve, a thin uniform warm dark-cocoa cavity directly under that same rim, and a soft fur-to-lip transition. It must read as one small mouth opening, never a detached round O. No vertical connector from nose to mouth, no remaining side smile arcs, no second outline, no nested cavity, no lollipop or exclamation-mark silhouette. Keep the petite nose itself unchanged. Lift the brows only subtly halfway.
Constraints: preserve Image 1 exactly everywhere outside the smallest mouth, philtrum, and brow regions — identical 1254×1254 composition, kangaroo identity, ear/head silhouette, eyes, irises, catchlights, muzzle markings, russet/tan plush micro-fuzz, nose, blush, lighting, scale, padding, and flat #00FF00 background. Keep eyes open. Maintain premium 2.5D plush-clay finish. Child-safe mouth with no tongue, teeth, fangs, highlights, split lobes, black cartoon outline, or inner shapes. No new elements, text, watermark, body, props, shadow, crop, or relighting. Background remains exact uniform #00FF00 and subject contains no key green.
```

### V2 full roar initial attempt

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face mask — v2 full roar state
Input images: Image 1 is the sole edit target and exact approved kangaroo identity anchor. The compatible topology specification below is authoritative.
Primary request: Redesign only the mouth and the tiny fur area immediately between mouth and nose into ONE contiguous delighted child-safe full roar that uses the exact same upper lip position, width, curvature, sampled-fur rim, and material as the v2 mid-roar: its upper rim follows the complete existing neutral U-smile curve from side to side, then the uniform warm dark-cocoa cavity expands naturally downward into one rounded open jaw. Replace the entire neutral smile drawing and vertical philtrum below the nose. No connector from nose to mouth, no remaining side smile arcs, no detached O, no second outline, no nested inner ring, no lollipop or exclamation-mark silhouette. Keep the petite nose itself unchanged. Gently lift both brows.
Constraints: preserve Image 1 exactly everywhere outside the smallest mouth, philtrum, and brow regions — identical 1254×1254 composition, kangaroo identity, ear/head silhouette, eyes, irises, catchlights, muzzle markings, russet/tan plush micro-fuzz, nose, blush, lighting, scale, padding, and flat #00FF00 background. Keep eyes open. Maintain premium 2.5D plush-clay finish with a dimensional sampled-fur lip transition. Cavity must be one uniform warm dark cocoa with no tongue, teeth, fangs, highlights, split lobes, black cartoon outline, or inner shapes. No new elements, text, watermark, body, props, shadow, crop, or relighting. Background remains exact uniform #00FF00 and subject contains no key green.
```

### V2 full roar targeted topology retry

```text
Use case: precise-object-edit
Asset type: reactive webcam game animal face mask — v2 full roar targeted topology retry
Input images: Image 1 is the sole edit target and exact v2 mid-roar identity/topology anchor.
Primary request: Expand only the lower half of Image 1’s existing shallow mouth opening downward into one moderately open rounded roar cavity. Preserve the existing mouth’s entire upper fur lip rim, left and right corners, horizontal width, curvature, position, and material exactly. The upper rim and corners must remain visually identical to Image 1; growth happens only downward from that same opening. Keep one uniform warm dark-cocoa cavity and a soft sampled-fur lower lip transition. Do not make the mouth wider or move it upward. Do not redraw the nose, muzzle, eyes, or head.
Constraints: preserve Image 1 exactly everywhere outside the smallest lower-mouth expansion region — identical 1254×1254 composition, kangaroo identity, silhouette, open eyes, brows, muzzle, nose, blush, micro-fuzz, lighting, scale, padding, and exact #00FF00 background. No tongue, teeth, fangs, highlights, split lobes, detached O, second outline, nested ring, lollipop, exclamation, smile arcs, black cartoon outline, text, watermark, body, props, shadow, crop, or relighting. The result must crossfade with Image 1 as one contiguous naturally enlarging mouth.
```

## Deterministic jaw construction

- `roar-mid-v2` imports only the selected shallow mouth through a feathered lower-muzzle mask; the nose and all non-jaw pixels stay v1-neutral.
- A small center connector mask is filled from horizontally sampled muzzle pixels, eliminating the lollipop/exclamation stem without flattening the surrounding micro-fuzz.
- The mid cavity is extracted from the authored source and normalized to RGB `(64, 24, 18)` with a one-pixel soft edge.
- `roar-v2` is created from the completed mid state by unioning a single antialiased lower extension into the same cavity. The extension is clipped below the shared upper rim, so no second rim or nested ring can exist in the source pair.
- The final jaw-local image is composited back over the exact neutral outside native ROI `(510, 1080, 740, 1212)`, proving zero outside-ROI drift.

## Export and audit evidence

- Runtime WebPs: native 1254×1254, quality 95, alpha quality 100, method 6, exact alpha.
- Runtime sizes: neutral 257,558 bytes; blink 264,618 bytes; roar-mid 255,812 bytes; roar 254,550 bytes.
- Actual public WebPs are decoded and passed through the exact four-state helper weights at jaw values `0`, `.125`, `.25`, `.375`, `.5`, `.625`, `.75`, `.875`, and `1`.
- At 380px, threshold-100 mouth segmentation reports exactly one significant component at every one of the nine samples. Largest mouth area progresses `79, 81, 167, 304, 332, 345, 594, 793, 803` pixels.
- At 96px, every non-neutral sample has exactly one significant threshold-100 mouth component; area progresses `8, 9, 15, 24, 26, 37, 51, 53` pixels.
- Visual sweeps are authoritative: `design/runtime/kangaroo/audit/helper-jaw-sweep-380-v2.png` and `design/runtime/kangaroo/audit/helper-jaw-sweep-96-v2.png`.
- State, hostile-background, masks, and multi-threshold helper evidence are under `design/runtime/kangaroo/audit/`; full metrics are in `design/runtime/kangaroo/manifest-v2.json`.
- Alpha is byte-identical across all four v2 states; bbox/padding remain `(219, 66, 1035, 1213)` / `(219, 66, 219, 41)`; one alpha component, zero enclosed holes, zero green-dominant partial-alpha fringe, exact `#00FF00` chroma exterior.
- Public and GitHub Pages v2 files are byte-identical and every runtime WebP contains `ALPH`.
- All v1 source, master, and runtime files retain their original checksums.
- Independent Gauntlet approval is intentionally deferred to a fresh critic.
