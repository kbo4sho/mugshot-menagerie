# Peekaboo Meerkat v1 prompts and provenance

## Route

- Generation: Codex built-in ImageGen, interrupted after the three chroma sources were written.
- Continuation: Cursor resumed from those generated sources. No new ImageGen in v1.
- Bumblebee v1 neutral was the finish, material, lighting, and centered-composition reference for the original generation.
- The generated meerkat neutral is the sole edit target for blink and roar localization.
- The installed chroma-removal helper extracts the neutral silhouette. Expression RGB is localized, and every final state receives the identical neutral alpha plane.

## Generated sources

- `design/runtime/meerkat/audit/neutral-generated-v1.png`
- `design/runtime/meerkat/audit/blink-generated-v1.png`
- `design/runtime/meerkat/audit/roar-generated-v1.png`

## Deterministic export contract

- Localized chroma masters: `design/runtime/meerkat/chroma/{neutral,blink,roar}-v1.png`
- Shared-alpha masters: `design/runtime/meerkat/alpha/{neutral,blink,roar}-v1.png`
- Runtime: `public/masks/meerkat/{neutral,blink,roar}-v1.webp`
- GitHub Pages mirror: `github-pages/public/masks/meerkat/{neutral,blink,roar}-v1.webp`
- Metrics and checksums: `manifest-v1.json`
