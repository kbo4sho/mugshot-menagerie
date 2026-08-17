# Bouncy Bunny v1 prompts and provenance

## Route

- Built-in Codex ImageGen; no CLI/API fallback.
- Use-case taxonomy: `stylized-concept` for the original neutral; `precise-object-edit` for both expression states.
- Finish/composition reference: `design/runtime/bumblebee/chroma/neutral-v1.png` (reference only, not an edit target).
- Neutral generated source: `/Users/kevinbolander/.codex/generated_images/01a00bfe-6e90-72f2-ad42-976742a3254c/exec-052d584a-47e4-40f5-9dbf-caa3a6f27946.png`.
- Blink generated source: `/Users/kevinbolander/.codex/generated_images/01a00bfe-6e90-72f2-ad42-976742a3254c/exec-fa7f859b-b4a9-4787-8d38-aeabf8ecc2ae.png`.
- Roar generated source: `/Users/kevinbolander/.codex/generated_images/01a00bfe-6e90-72f2-ad42-976742a3254c/exec-4cd0dde1-b6a7-4773-9974-8d8c268bf9f4.png`.
- Durable generated-source copies: `design/runtime/bunny/audit/generated-neutral-v1.png`, `design/runtime/bunny/audit/generated-blink-v1.png`, and `design/runtime/bunny/audit/generated-roar-v1.png`.
- Post-processing and audit are deterministic in `design/runtime/bunny/audit/export_and_audit.py`.
- Local background extraction used the installed ImageGen `remove_chroma_key.py` helper with border auto-key, soft matte, thresholds 12/220, and despill.
- Blink and roar are localized to compact facial ROIs over the exact neutral, clipped to a 20-pixel-eroded safe interior so state RGB cannot touch the perimeter, then all states receive the neutral alpha. The keyed subject is scaled uniformly to 94% on the original 1254-square canvas to increase ear-tip padding.
- WebP exports use quality 95, alpha quality 100, method 6, and exact alpha. The hostile-background and copy+lighter 380-pixel review sheets decode the actual shipped WebPs.

## Neutral prompt

```text
Use case: stylized-concept
Asset type: reactive browser-game animal face mask, neutral state
Input images: Image 1 is a strict finish, material, lighting, framing, eye-scale, and chibi-proportion reference only; do not copy its bee anatomy or design.
Primary request: Create one original front-facing chibi rabbit head named Bouncy Bunny on a perfectly flat solid #00FF00 chroma-key background for local background removal.
Scene/backdrop: exactly one uniform pure #00FF00 field, edge to edge, with no gradient, texture, shadow, glow, reflection, floor, horizon, vignette, or lighting variation.
Subject: unmistakable rabbit head only. Rounded cream to light-tan plush-fur head, two very long upright plush ears fully visible with soft pink inner panels, subtle soft cheek tufts, tiny triangular pink-brown nose, compact pale muzzle, gentle cheek blush, and giant glossy honey-brown eyes. Neutral expression has a small closed gentle smile with no visible teeth.
Style/medium: premium polished 2.5D plush-clay character render with delicate micro-fuzz, tactile softness, rounded sculpted forms, warm studio key light and crisp readable details matching Image 1's finish.
Composition/framing: perfectly centered, straight-on, symmetrical head, no body or neck. Both tall ear tips completely in frame with generous green padding above and on every side. Face should fill the frame while retaining generous ear-tip clearance and lower padding. Designed to read clearly when rendered at 380 px.
Lighting/mood: cheerful, safe, warm, playful; dimensional lighting on the subject only.
Color palette: cream and light tan fur, soft pink ear interiors and blush, honey-brown irises; never use any #00FF00 or green hue inside the rabbit.
Materials/textures: even micro-fuzz and plush-clay finish; no long flyaway hairs crossing onto the background.
Constraints: exactly one head, exactly two long upright rabbit ears, exactly two eyes, head and ears fully in frame; rabbit species cues must dominate. No text, no watermark, no cast shadow, no contact shadow, no transparent areas.
Avoid: mouse, hamster, cat, bear, fox, puppy, body, neck, shoulders, paws, carrot, prop, bow, accessory, collar, whiskers extending into the background, extra teeth, open mouth, visible tongue, fangs, floor plane, pedestal, background artifacts.
```

## Blink prompt

```text
Use case: precise-object-edit
Asset type: reactive browser-game animal face mask, blink state
Input images: Image 1 is the sole edit target and identity anchor.
Primary request: Change only the rabbit's facial expression to a delighted full happy blink.
Expression change: both giant eyes are completely closed as two smooth symmetrical upward-curving dark brown lash arcs embedded naturally in the face; add a tiny joyful cheek lift. Keep the small mouth fully closed in the same gentle smile. No visible teeth and no tongue.
Exact invariants: preserve the identical rabbit identity, head silhouette, two long upright ear shapes and positions, pink inner ears, fur color, cheek tufts, eyebrows, nose, compact pale muzzle, blush, lighting, micro-fuzz texture, scale, centering, crop, padding, and perfectly uniform pure #00FF00 background from Image 1. Do not redraw or restyle any region outside the two eye areas and minimal cheek-lift area.
Constraints: rabbit head only; no body or neck; no text; no watermark; no shadow; no floor; no green inside the subject.
Avoid: open eyes, squint with visible pupils, wink, asymmetry, open mouth, teeth, tongue, fangs, extra eyelashes, mouse/hamster/cat traits, props, accessories, background change, silhouette drift, texture drift.
```

## Roar prompt

```text
Use case: precise-object-edit
Asset type: reactive browser-game animal face mask, delighted roar state
Input images: Image 1 is the sole edit target and identity anchor.
Primary request: Change only the rabbit's facial expression to a delighted compact safe open-mouth roar.
Expression change: open the mouth into one small centered vertical O beneath the unchanged nose and muzzle. The mouth has a dark warm interior, a small warm pink tongue low inside, and exactly two small rounded upper bunny incisors together at the top center. Incisors are short, broad, softly rounded, friendly, and unmistakably rabbit teeth—not pointed, not fangs. Lift both eyebrows slightly for joyful excitement. Keep both giant honey-brown eyes fully open and preserve their exact identity.
Exact invariants: preserve the identical rabbit identity, head silhouette, two long upright ear shapes and positions, pink inner ears, fur color, cheek tufts, eye size/color/placement, nose, compact pale muzzle, blush, lighting, micro-fuzz texture, scale, centering, crop, padding, and perfectly uniform pure #00FF00 background from Image 1. Do not redraw or restyle any region outside a compact mouth/lower-muzzle region plus the two eyebrow regions.
Constraints: exactly two upper incisors and no other teeth; rabbit head only; no body or neck; no text; no watermark; no shadow; no floor; no green inside the subject.
Avoid: fangs, pointed teeth, rows of teeth, more than two teeth, beaver-like giant teeth, huge mouth, scary expression, tongue protruding, closed mouth, squint, eye drift, mouse/hamster/cat traits, props, accessories, background change, silhouette drift, texture drift.
```
