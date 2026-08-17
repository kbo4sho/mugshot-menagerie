# Silly Shark v2 provenance

## Repair brief

Independent critic found that v1's neutral smile spans native x=496–753 while the roar cavity spans only x=545–708. At production roar weights 0.10, 0.25, 0.50, and 0.75, the unmatched side spans and discrete warm tongue produced a detached lower oval, pacifier-like crossing bar, and residual hooks.

## Source-preserving route

- No new ImageGen call.
- v1 remains intact.
- v2 neutral and blink alpha, chroma, and runtime files are byte-identical copies of v1.
- v2 roar starts from `design/runtime/shark/alpha/roar-v1.png`.
- The exact connected neutral smile component from `design/runtime/shark/alpha/neutral-v1.png` defines a smooth supersampled cavity whose upper Bezier edge follows and absorbs the full smile span.
- Only the native ROI `[468, 892, 786, 1114]` can change.
- The v1 central O is fully cleaned from the target ROI before one continuous dark-to-warm cavity is rendered without a discrete tongue island.
- Exactly two small rounded deterministic tooth caps attach to the new upper boundary.
- The neutral alpha channel is assigned unchanged to every v2 state.

## Export and review contract

- Master PNGs: `design/runtime/shark/{alpha,chroma}/{state}-v2.png`.
- Runtime WebPs: `public/masks/shark/{state}-v2.webp`.
- Byte-identical Pages copies: `github-pages/public/masks/shark/{state}-v2.webp`.
- Runtime blend proofs use the production copy-plus-lighter weights and the exact requested checkpoints: 0.10, 0.25, 0.50, and 0.75 at both 380px and 96px.
- Perceptual topology is probed at nine luminance thresholds from 105 through 185 using tooth-aware connected components in a tight mouth-only ROI. Only the two intentional bright tooth boxes are filled for connectivity; detached lower forms remain unaltered by the probe.
- A 24-frame, 936ms production-mapped ramp is exported at 380px and 96px.
