import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

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
  assert.match(html, />85</);
  assert.match(html, /6<\/strong><span>Friends at once/);
  assert.match(html, /0<\/strong><span>Photos saved/);
  assert.match(html, /no account and no uploads/i);
  assert.match(html, /face detection runs in your browser/i);
  assert.doesNotMatch(html, /codex-preview|starter loading skeleton/i);
});

test("ships exactly 85 unique animals including the 25-species expansion", async () => {
  const page = await readFile(pageUrl, "utf8");
  const roster = page.slice(page.indexOf("const ANIMALS"), page.indexOf("const CONFETTI"));
  const entries = [...roster.matchAll(/\{ id: "([^"]+)", name: "([^"]+)"/g)].map((match) => ({ id: match[1], name: match[2] }));
  assert.equal(entries.length, 85);
  assert.equal(new Set(entries.map(({ id }) => id)).size, 85);
  assert.equal(new Set(entries.map(({ name }) => name)).size, 85);

  const required = [
    "walrus", "orangutan", "baboon", "platypus", "anteater", "tapir", "okapi", "hyena", "warthog", "buffalo",
    "camel", "porcupine", "skunk", "beaver", "hedgehog", "rooster", "turkey", "puffin", "cockatoo", "ostrich",
    "squid", "lobster", "seahorse", "stingray", "pufferfish",
  ];
  required.forEach((id) => assert.ok(entries.some((animal) => animal.id === id), `missing ${id}`));
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
  assert.match(page, /drawAnimal\(ctx, animalIndex/);
  assert.match(css, /\.animal-ticket\s*\{[^}]*pointer-events:\s*none/s);
});
