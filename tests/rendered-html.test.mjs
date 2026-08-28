import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { selectRenderedMaskState } from "../app/rendered-mask-blend.mjs";

const pageUrl = new URL("../app/page.tsx", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the Giggle Zoo experience and privacy promise", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /Giggle Zoo/);
  assert.match(html, /Your face just/);
  assert.match(html, />100</);
  assert.match(html, /6<\/strong><span>Friends at once/);
  assert.match(html, /0<\/strong><span>Photos saved/);
  assert.match(html, /no account and no uploads/i);
  assert.match(html, /face detection runs in your browser/i);
  assert.doesNotMatch(html, /codex-preview|starter loading skeleton/i);
});

test("keeps the 100-animal catalog and ships only rendered packs live", async () => {
  const page = await readFile(pageUrl, "utf8");
  const roster = page.slice(page.indexOf("const ANIMAL_ROSTER"), page.indexOf("const CONFETTI"));
  const entries = [...roster.matchAll(/\{ id: "([^"]+)", name: "([^"]+)"/g)].map((match) => ({ id: match[1], name: match[2] }));
  assert.equal(entries.length, 100);
  assert.equal(new Set(entries.map(({ id }) => id)).size, 100);
  assert.equal(new Set(entries.map(({ name }) => name)).size, 100);

  const required = [
    "walrus", "orangutan", "baboon", "platypus", "anteater", "tapir", "okapi", "hyena", "warthog", "buffalo",
    "camel", "porcupine", "skunk", "beaver", "hedgehog", "rooster", "turkey", "puffin", "cockatoo", "ostrich",
    "squid", "lobster", "seahorse", "stingray", "pufferfish", "horse", "donkey", "sheep", "squirrel", "mouse",
    "hamster", "duck", "goose", "swan", "crow", "bumblebee", "butterfly", "ladybug", "mantis", "snail",
  ];
  required.forEach((id) => assert.ok(entries.some((animal) => animal.id === id), `missing ${id}`));

  const versionBlock = page.match(/const RENDERED_MASK_VERSIONS:[^{]+\{([\s\S]*?)\n\};/);
  assert.ok(versionBlock, "rendered mask registry is missing");
  const packs = [...versionBlock[1].matchAll(/(\w+):\s*"(v\d+)"/g)].map(([, animal]) => animal);
  assert.equal(packs.length, 100);
  assert.match(page, /const ANIMALS: Animal\[] = ANIMAL_ROSTER\.filter/);
  assert.ok(packs.every((id) => entries.some((animal) => animal.id === id)), "a rendered pack is missing from the catalog");
  assert.deepEqual(new Set(packs), new Set(entries.map(({ id }) => id)), "every catalog animal should have a rendered pack");
});

test("keeps camera, tracking, shuffle, stop, fullscreen, and renderer diagnostics wired", async () => {
  const [page, css] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);
  assert.match(page, /numFaces:\s*6/);
  assert.match(page, /event\.code === "Space"/);
  assert.match(page, /randomAnimal\(track\.animal\)/);
  assert.match(page, /while \(pick === except\)/);
  assert.match(page, /getTracks\(\)\.forEach\(\(track\) => track\.stop\(\)\)/);
  assert.match(page, /requestFullscreen/);
  assert.match(page, /<DiagnosticSheet poseName="neutral"/);
  assert.match(page, /<DiagnosticSheet poseName="blink"/);
  assert.match(page, /<DiagnosticSheet poseName="roar"/);
  assert.match(page, /<DiagnosticSpotlight animalIndex=\{focusIndex\} poseName="neutral"/);
  assert.match(page, /<DiagnosticSpotlight animalIndex=\{focusIndex\} poseName="blink"/);
  assert.match(page, /<DiagnosticSpotlight animalIndex=\{focusIndex\} poseName="roar"/);
  assert.match(page, /data-focus-animal=\{animal\.id\}/);
  assert.match(page, /<RenderedSpotlight key=\{poseName\}/);
  assert.match(page, /bumblebee-chibi-neutral-v1\.webp/);
  assert.match(page, /data-review-source=\{renderedStates \? "imagegen" : "canvas"\}/);
  assert.match(page, /const RENDERED_MASK_SOURCES/);
  assert.match(page, /preloadRenderedMask\(ANIMALS\[animalIndex\]\.id\)/);
  assert.match(page, /drawRenderedMask\(ctx, animal, pose, coverageX, coverageY\)/);
  assert.match(page, /if \(RENDERED_MASK_SOURCES\[animal\.id\]\) \{/);
  assert.match(page, /selectRenderedMaskState\(/);
  assert.doesNotMatch(page, /blendRenderedMaskRgba\(/);
  assert.match(page, /<RenderedMaskProof animalIndex=\{focusIndex\}/);
  assert.match(page, /forcedAnimalRef\.current \?\? randomAnimal\(\)/);
  assert.match(page, /drawAnimal\(ctx, animalIndex/);
  assert.match(css, /\.animal-ticket\s*\{[^}]*pointer-events:\s*none/s);
});

test("ships every registered rendered runtime state pack with transparency", async () => {
  const page = await readFile(pageUrl, "utf8");
  const versionBlock = page.match(/const RENDERED_MASK_VERSIONS:[^{]+\{([\s\S]*?)\n\};/);
  assert.ok(versionBlock, "rendered mask registry is missing");
  const packs = [...versionBlock[1].matchAll(/(\w+):\s*"(v\d+)"/g)].map(([, animal, version]) => ({ animal, version }));
  assert.ok(packs.length > 0, "rendered mask registry is empty");
  for (const { animal, version } of packs) {
    for (const state of ["neutral", "blink", "roar"]) {
      const asset = await readFile(new URL(`../public/masks/${animal}/${state}-${version}.webp`, import.meta.url));
      assert.equal(asset.subarray(0, 4).toString(), "RIFF");
      assert.ok(asset.includes(Buffer.from("ALPH")), `${animal} ${state} mask is missing an alpha channel`);
    }
  }

  const roarMidVersionBlock = page.match(/const RENDERED_MASK_ROAR_MID_VERSIONS:[^{]+\{([\s\S]*?)\n\};/);
  assert.ok(roarMidVersionBlock, "rendered mask mid-roar registry is missing");
  const roarMids = [...roarMidVersionBlock[1].matchAll(/(\w+):\s*"(v\d+)"/g)]
    .map(([, animal, version]) => ({ animal, version }));
  const registeredAnimals = new Set(packs.map(({ animal }) => animal));
  for (const { animal, version } of roarMids) {
    assert.ok(registeredAnimals.has(animal), `${animal} configures a mid-roar without a registered rendered pack`);
    const asset = await readFile(new URL(`../public/masks/${animal}/roar-mid-${version}.webp`, import.meta.url));
    assert.equal(asset.subarray(0, 4).toString(), "RIFF");
    assert.ok(asset.includes(Buffer.from("ALPH")), `${animal} mid-roar mask is missing an alpha channel`);
  }
});

test("rendered masks select one authored expression without transparent blending", () => {
  assert.equal(selectRenderedMaskState(0, 0, false), "neutral");
  assert.equal(selectRenderedMaskState(.7, 0, false), "blink");
  assert.equal(selectRenderedMaskState(.7, .7, false), "roar");
  assert.equal(selectRenderedMaskState(0, .4, true), "roarMid");
  assert.equal(selectRenderedMaskState(0, .4, false), "neutral");
});
