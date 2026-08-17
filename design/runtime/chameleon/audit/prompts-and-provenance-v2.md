# Color-Pop Chameleon v2 repair provenance

No new ImageGen call was made for v2. The accepted v1 neutral, blink, roar, magenta matte, and locked alpha were preserved; the critic's correction required deterministic mouth geometry and sampled-pixel repair rather than a fresh generative interpretation. The original built-in ImageGen prompt set and generated sources remain documented in `prompts-and-provenance-v1.md`.

## Exact repair brief

```text
Build Chameleon v2 four-state non-destructively, preserving v1 and accepted neutral/blink/roar/alpha. Repair/authored roar-mid geometry from the neutral baseline: it must be a SHALLOW opening whose upper rim begins exactly on and absorbs the neutral smile, with target pixels painting out both side-smile remnants using sampled green muzzle texture. No separate lower oval. Test actual helper at jaw .1,.2,.3,.4,.5 at 380/96: one continuously thickening mouth, no simultaneous smile arc/opening/overlap/side marks. Also verify mid→roar .6-.9 remains one cavity; if v1 roar upper rim is incompatible, minimally localize v2 roar too. Use visual proof plus perceptual multi-threshold that doesn't hide lighter shapes. Preserve magenta matte/shared alpha/outside ROI0. Export all four v2 states/public/pages, v1 preserved. No app/registry/ledger edits/self-approval.
```

## Deterministic implementation

- Source identity: `design/runtime/chameleon/alpha/{neutral,blink,roar-mid,roar}-v1.png`.
- Neutral and blink v2 are pixel-identical copies of their accepted v1 alpha masters.
- A dark-pixel smile mask is confined to the muzzle and expanded/feathered. Its target pixels are replaced with a vertically adjacent sample of the same green pebbled muzzle texture.
- The roar-mid cavity spans x=548..707. Its upper edge follows the v1 smile curve `y = 949 - 0.00425 * (x - 627.5)^2`; the lower edge adds only 3..38 pixels of depth. Consequently the opening begins on the existing smile and cannot form a detached lower oval.
- The cavity uses a warm cocoa-to-coral gradient with subtle luminance texture inherited from the sampled muzzle. Its lip treatment is a single connected shadow/lower highlight ring.
- V1 roar contained faint detached side-smile remnants at native scale. V2 roar changes only those side regions using the same healed muzzle texture; the accepted central O cavity is preserved.
- The hard repair ROI is `[492, 874, 762, 1050]`. Measured repair delta outside that ROI is zero for every v2 state.
- The exact semantic helper branch from `app/rendered-mask-blend.mjs` is reproduced in the audit script for jaw weights 0.1 through 0.9.
- Perceptual topology is checked at 380px after a gentle 1.6px low-pass filter, at RMS color-delta thresholds 3, 6, 10, 16, and 24. This includes light changes while suppressing codec/pebble noise. A secondary component at least 5% of the dominant mouth would fail.
- Runtime exports are 1254px WebP, quality 95, alpha quality 100, method 6, exact alpha.

## Build source

`design/runtime/chameleon/audit/build_v2_repair_audit.py`
