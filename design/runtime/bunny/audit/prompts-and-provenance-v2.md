# Bouncy Bunny v2 geometry-repair prompt and provenance

## Route and source preservation

- Built-in Codex ImageGen; no CLI/API fallback.
- One targeted neutral geometry edit was used; there was no generated retry.
- Sole edit target: `design/runtime/bunny/chroma/neutral-v1.png`.
- Built-in generated source: `/Users/kevinbolander/.codex/generated_images/01a00bfe-6e90-72f2-ad42-976742a3254c/exec-d9f36605-92e2-4611-b519-dddf49adb04e.png`.
- Durable generated copy: `design/runtime/bunny/audit/generated-neutral-v2.png`.
- Chroma extraction used the installed ImageGen helper with border auto-key, soft matte, thresholds 12/220, and despill.
- Deterministic build/audit script: `design/runtime/bunny/audit/export_and_audit_v2.py`.
- The generated edit supplied the raised crown surface. Only its center crown was transplanted over the approved v1 neutral; the v1 ears, facial identity, palette, texture, features, and lower silhouette remain pixel-preserved outside that region.
- The crown is locally expanded upward by 28 native pixels for tilt/bounce reserve. Blink and roar are rebuilt as localized expression ROIs over the repaired v2 neutral, clipped to a 20-pixel-eroded interior. All three v2 states receive the same locked alpha.
- A deterministic partial-edge cleanup caps residual green-dominant RGB on low-alpha matte pixels. This reduced the audited sparse green-tinted partial-edge count from 748 in v1 to 0 in v2.
- Runtime exports are 1254-square WebPs at quality 95, alpha quality 100, method 6, and exact alpha. The Pages copies are byte-identical.

## Exact targeted edit prompt

```text
Use case: precise-object-edit
Asset type: reactive browser-game animal face mask, neutral geometry repair
Input images: Image 1 is the sole edit target and identity anchor.
Primary request: Change only the rabbit's upper forehead geometry between the two ears. Raise and enlarge the solid cream-fur face crown into the green gap between the inner ear bases, creating a broader smooth rounded forehead dome that begins about 85 to 100 pixels higher at the vertical centerline of this 1254 x 1254 image. The repaired centerline crown should reach approximately y=420 to y=430, with continuous fully opaque cream plush fur across the tracked forehead zone. Blend the new crown seamlessly into the existing ear roots and forehead with matching micro-fuzz, color, lighting, and curvature.
Exact invariants: keep the identical rabbit identity and expression, both long ears' shapes/positions/pink interiors, eye size/color/placement, eyebrows, nose, muzzle, smile, blush, cheek tufts, lower head silhouette, palette, lighting, micro-fuzz finish, scale, centering, and crop. Keep both ear tips fully visible with at least the existing green clearance above them. Keep the perfectly uniform pure #00FF00 background everywhere outside the subject.
Constraints: change only the cream-fur crown/forehead bridge between the ears; no body, neck, paws, props, accessories, text, watermark, cast shadow, floor, or green inside the subject.
Avoid: moving or shortening the ears, changing facial features, adding a third tuft or accessory, flattening the crown, covering the pink ear interiors, asymmetry, texture drift, background variation, silhouette changes anywhere except the requested raised center forehead crown.
```

## Canonical geometry model

- The proof uses the unchanged runtime transform: `drawX=-190`, `drawY=-225`, `drawSize=380`, and rendered coverage `1.42`.
- MediaPipe landmark 10 is fixed at `(190, 144.5)` in the 380 asset for the static canonical pose, matching the independent critic's measurement.
- The canonical tracked-face outline uses side landmarks 234/454 at a 218-unit face width and landmark 152 at approximately y=310.1 in asset space.
- Stress cases rotate the complete tracked face by ±8 degrees and shift it 3.5 asset pixels upward relative to the mask, representing a modest worst-direction bounce.
- Pass requires zero tracked-face pixels below alpha 250 and at least 12 pixels of continuous opaque crown above landmark 10.
