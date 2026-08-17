# Rendered mask production ledger

## Goal

Replace the remaining 99 procedural animal faces with consistent, premium chibi 2.5D plush-clay renders. Each animal ships as a transparent neutral, blink, and child-safe roar state driven by the existing live face-tracking renderer.

## Locked reference

- Visual bar: `design/runtime/bumblebee/alpha/{neutral,blink,roar}-v1.png`
- Runtime proof: `/?gallery=bumblebee`
- Runtime geometry: shared rendered-mask draw path in `app/page.tsx`

## Gauntlet bar

| Priority | Dimension | Probe | Losing condition |
| --- | --- | --- | --- |
| P0 | Species readability | Inspect each state at thumbnail and full size. | The animal is ambiguous or depends on text to be recognized. |
| P0 | Three-state identity | Compare silhouette, proportions, palette, materials, and stable facial landmarks across neutral, blink, and roar. | Any state looks like a redesigned or different character. |
| P0 | Runtime alignment | Compare state bounding boxes, scale, centering, padding, and facial-feature positions. | Crossfades visibly jump, double, crop, or change scale. |
| P0 | Transparent matte | Inspect alpha assets over light, dark, saturated green, and saturated magenta backgrounds; audit transparent corners. | Key-color fringe, opaque backdrop, holes, clipped detail, or dirty corners are visible. |
| P1 | Approved finish | Compare material richness, lighting, fuzzy/plush detail, eye treatment, and chibi proportions with Bumblebee. | The result reads flatter, cheaper, harsher, or less polished than the approved bar. |
| P1 | Expression clarity and safety | Inspect closed-eye blink and open-mouth roar at thumbnail size. | Blink is unclear; roar reads frightening, aggressive, or anatomically broken. |
| P0 | Product regressions | Build/test plus live camera, shuffle, stop-camera, full-screen, mobile, and up-to-six-face checks after integration waves. | Existing privacy, tracking, controls, shuffle, or multi-face behavior regresses. |

## Constraints

- Camera frames remain local; no recording, uploads, analytics, or storage.
- Preserve the existing tracking, scale, tilt, expression signals, shuffle rules, controls, and six-face support.
- Do not redesign the site while producing masks.
- Built-in ImageGen with removable chroma-key backgrounds remains the approved generation path.
- The live roster is filtered to the 41 independently won rendered packs until ImageGen returns. Keep the full 100-animal catalog in `ANIMAL_ROSTER`.
- User authorized this interim 41-animal Pages publish. Resume the remaining 59 when ImageGen is back on Friday 2026-08-21.

## Progress

| Wave | Animals | Build | Independent critic | Runtime integration |
| --- | --- | --- | --- | --- |
| Reference | bumblebee | Complete | Approved by user | Complete |
| 01a | capybara | V2 complete | WIN | Complete |
| 01b | frog | Complete | WIN | Complete |
| 01c | pigeon | V2 complete | WIN | Complete |
| 02a | raccoon | Complete | WIN | Complete |
| 02b | axolotl | V2 complete | WIN | Complete |
| 02c | cow | V2 complete | WIN | Complete |
| 03a | llama | Complete | WIN | Complete |
| 03b | otter | V2 complete | WIN | Complete |
| 03c | tiger | V3 registered | WIN | Complete |
| 04a | goat | Complete | WIN | Complete |
| 04b | panda | V2 registered | WIN | Complete |
| 04c | elephant | V2 complete | WIN | Complete |
| 05a | lion | Complete | WIN | Complete |
| 05b | giraffe | Complete | WIN | Complete |
| 05c | monkey | Complete | WIN | Complete |
| 06a | koala | Complete | WIN | Complete |
| 06b | hippo | Complete | WIN | Complete |
| 06c | zebra | Complete | WIN | Complete |
| 07a | fox | Complete | WIN | Complete |
| 07b | bunny | V2 complete | WIN | Complete |
| 07c | pig | Complete | WIN | Complete |
| 08b | cat | Complete | WIN | Complete |
| 09a | penguin | V2 complete | WIN | Complete |
| 10a | deer | Complete | WIN | Complete |
| 11a | shark | V2 complete | WIN | Complete |
| 11b | octopus | Complete | WIN | Complete |
| 12a | unicorn | V2 complete | WIN | Complete |
| 13b | gorilla | V2 four-state bridge complete | WIN | Complete |
| 14a | meerkat | V1 complete | WIN | Complete |
| 09b | sloth | V5 four-state bridge complete | WIN | Complete |
| 09c | bear | Complete | WIN | Complete |
| 10b | flamingo | Complete | WIN | Complete |
| 10c | parrot | V3 complete | WIN | Complete |
| 12b | crocodile | Complete | WIN | Complete |
| 12c | kangaroo | V9 cavity-preserving blend complete | WIN | Complete |
| 11c | chameleon | V2 four-state bridge complete | WIN | Complete |
| 13a | rhino | V2 four-state bridge complete | WIN | Complete |
| 13c | lemur | V7 cavity-preserving blend complete | WIN | Complete |
| 08c | owl | Complete | WIN | Complete |
| 08a | dog | Complete | WIN | Complete |

## Parked until ImageGen returns — Friday 2026-08-21

Live site and shuffle currently expose only the 41 Complete / WIN rows above. Procedural unfinished animals stay in `ANIMAL_ROSTER` but are not playable.

**Next animal:** redpanda (Red Panda Rocket), then leopard, cheetah, wolf, moose, ram, alpaca, and the rest of `ANIMAL_ROSTER` in existing order.

**Resume path:** ImageGen on chroma → extract → localize blink/roar onto shared alpha → independent critic → wire on WIN → unfilter that id by adding it to `RENDERED_MASK_VERSIONS`.

Remaining ids: redpanda, leopard, cheetah, wolf, moose, ram, alpaca, toucan, peacock, pelican, eagle, bat, seal, dolphin, whale, crab, jellyfish, turtle, snake, armadillo, walrus, orangutan, baboon, platypus, anteater, tapir, okapi, hyena, warthog, buffalo, camel, porcupine, skunk, beaver, hedgehog, rooster, turkey, puffin, cockatoo, ostrich, squid, lobster, seahorse, stingray, pufferfish, horse, donkey, sheep, squirrel, mouse, hamster, duck, goose, swan, crow, butterfly, ladybug, mantis, snail.

## Stop policy

Parked until ImageGen is back on Friday 2026-08-21. Then continue until all remaining packs win the bar and are integrated, the user stops the loop, or a repeated generation/transparency failure requires a new user-authorized production path.
