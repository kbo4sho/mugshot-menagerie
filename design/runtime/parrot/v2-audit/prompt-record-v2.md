# Party Parrot v2 repair record

Critic gap: the v1 roar's pale lower mandible wrapped the full cavity like an ivory horseshoe. At 96px and intermediate copy+lighter weights it read as a white smile/tooth rim and a second mouth beneath the still-visible neutral beak tip.

## One permitted targeted ImageGen edit

```text
Use case: precise-object-edit
Asset type: reactive webcam parrot mask, roar-state beak transition repair
Input images: Image 1 is the sole edit target, the exact Party Parrot v1 roar state.
Primary request: Change only the open beak and mouth geometry inside the compact central mouth ROI. Remove the entire pale ivory horseshoe that currently wraps up both sides of the burgundy mouth cavity. Replace those pale side bands with anatomically appropriate dark charcoal horn hinge material and the exact surrounding scarlet cheek feathers. Keep one uninterrupted, centered deep-burgundy cavity beginning directly beneath and overlapping the existing upper-beak seam. Add one compact dark horn lower mandible attached immediately below the cavity: rounded-tapered, clearly beak material, no more than about 45% of the cavity width, confined below the cavity, with no pale outline.
Transition requirement: the target cavity and hinge must occupy the same central footprint as the neutral upper-beak tip/seam so a crossfade reads as one continuously opening parrot beak, never a second mouth underneath.
Constraints: preserve absolutely every element outside the mouth/beak ROI unchanged: exact character identity, eyes, brows, feather crown, scarlet/golden/cobalt feather map, blush, scale, position, silhouette, lighting, texture, canvas, padding, and transparent background. Preserve the exact upper pale horn beak and charcoal tip above the cavity. No pale side-wrapping rim, no white smile band, no teeth, no tongue, no uvula, no disconnected cavity, no separate second mouth, no human smile. No new elements, body, props, text, logo, watermark, crop, or shadow.
Avoid: ivory horseshoe, tooth-like band, broad lower smile, floating lower beak, duplicated beak tip, mammal mouth, aggressive gape, changes outside the mouth ROI.
```

Generated source: `$CODEX_HOME/generated_images/01a00c39-6af3-7712-8acf-546800a5e8cb/exec-17ee5e6f-1f3d-4d99-bf92-52c204e1a4aa.png`

Workspace copy: `design/runtime/parrot/v2-audit/roar-imagegen-target-v2.png`

The edit target replaced the pale horseshoe with a dark U, but the dark side arms still wrapped the cavity and therefore did not satisfy the compact-lower-mandible requirement. It was retained as audit evidence but not selected for the shipped v2 master.

## Selected deterministic repair

- Neutral and blink v2 masters are pixel-identical copies of v1.
- Roar v2 starts from the exact v1 roar.
- A soft mouth-only mask restores exact neutral dark hinge and scarlet feather pixels over the pale side rails and broad pale bottom band.
- The original centered burgundy cavity remains uninterrupted and overlaps the neutral upper-beak seam.
- Only the small central charcoal point below the cavity remains as the compact lower mandible.
- The exact v1 alpha is reapplied to all states.
- The repair changes no pixel outside `design/runtime/parrot/v2-audit/roar-final-localization-mask-v2.png`.
- Runtime export remains 1344×1344, WebP q95, alpha q100, method 6, exact mode.
