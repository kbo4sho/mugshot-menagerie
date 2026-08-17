# Sleepy Sloth v3 geometry-repair provenance

V3 is a deterministic, non-destructive geometry repair. It makes no new ImageGen call and preserves v1 and v2.

## Preserved inputs

- Neutral pixel source: `design/runtime/sloth/alpha/neutral-v1.png`
- Blink pixel source: `design/runtime/sloth/alpha/blink-v1.png`
- Existing raw roar source: `design/runtime/sloth/audit/generated-roar-v2.png`
- Original v2 ImageGen prompt and source provenance: `design/runtime/sloth/audit/provenance-v2.md`

The v3 neutral and blink files are byte-identical to v1. All three v3 states use the exact v1 neutral alpha plane. The v3 roar is neutral pixel-for-pixel outside `roar-localization-mask-v3.png`.

## Target-geometry repair

1. Reuse the existing generated O mouth and its muzzle texture.
2. Translate the complete local mouth/muzzle patch upward 16 native pixels. This places the cavity's upper rim onto the neutral smile's central span rather than below it.
3. Localize a wide upper lobe across the entire obsolete smile and an overlapping lower lobe across the translated O. The target therefore paints the left/right smile portions with matching generated muzzle while the central span becomes the opening's connected upper rim.
4. Rebuild the connected cavity's perceptual hierarchy: the upper bridge stays very deep cocoa, then continuously—not as an island—rises into muted warm cocoa at the lower interior. During low-weight linear blends, the lower cavity cannot become visible before its bridge.
5. Feather the deterministic source into neutral, preserve the shared v1 alpha, and export 1024×1024 WebP q95 with alpha quality 100.

Derived source:

- `design/runtime/sloth/audit/generated-roar-geometry-v3.png`

## Evidence

- `production-roar-weights-380-v3.png` — production copy+lighter at 0/.10/.25/.50/.75/1.
- `production-roar-weights-96-v3.png` — the same weights at 96px, enlarged 4×.
- `production-roar-ramp-936ms-380-v3.gif` and `production-roar-ramp-936ms-96-v3.gif` — 24 samples of the production 936ms smoothstep curve, GIF-encoded at 960ms because GIF timing is centisecond-based.
- `perceptual-component-thresholds-v3.png` — central mouth probe at weights .10/.25/.50/.75 and perceptual luminance thresholds 125/145/155/165.
- `v1-v2-v3-roar-compare-380.png` — direct comparison at the four critic weights.
- `manifest-v3.json` — exact component areas/bounds/runs across thresholds 105–165, hashes, alpha and copy parity, geometry, and matte metrics.

The significant-component probe uses the central mouth-only runtime ROI `[168,255,212,289]` and excludes components under 64 pixels as antialiasing or muzzle-texture specks. At each requested weight, every threshold from 105 through 165 reports one significant visible mouth component.
