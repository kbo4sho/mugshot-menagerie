# Giggle Zoo project guide

## Product

Giggle Zoo is a kid-focused, browser-based webcam game. It detects up to six faces and draws a randomly selected, reactive animal mask over each face. The experience should feel playful, safe, immediate, and unmistakably zoo themed.

The public site is https://kbo4sho.github.io/mugshot-menagerie/. The repository name and URL slug remain `mugshot-menagerie`, while the visible product name is **Giggle Zoo!**.

## Product promises

- Camera frames stay in the browser. Never add recording, uploads, analytics, or photo storage without explicit approval.
- Keep copy friendly for children and include clear grown-up privacy guidance.
- Preserve full-screen mode, keyboard controls, touch controls, and explicit camera shutdown.
- Animal masks should cover the full face, track position/scale/tilt smoothly, and react to blinks and mouth movement.
- A shuffle must not immediately repeat the animal currently on screen.
- Maintain support for up to six simultaneous faces.

## Architecture

- `app/page.tsx`: webcam lifecycle, MediaPipe Face Landmarker integration, face tracking, shuffle behavior, and all canvas-drawn animal masks.
- `app/globals.css`: responsive zoo-themed interface and full-screen camera styling.
- `app/layout.tsx`: document metadata.
- `github-pages/` and `vite.pages.config.ts`: static GitHub Pages entry point.
- `docs/`: generated GitHub Pages output. Rebuild it; do not hand-edit it.
- `.openai/hosting.json`: existing Sites project binding. Preserve its `project_id`.

## Local workflow

Requires Node.js 22.13 or newer.

```bash
npm install
npm run dev
```

Camera testing requires `localhost` or HTTPS and an explicit browser permission grant.

## Validation

Run these checks before shipping product changes:

```bash
npm run build:pages
npm run build
npm test
```

For camera or mask changes, also check one live face, shuffle behavior, camera-off behavior, and full-screen layout in a real browser. Check a narrow mobile viewport for layout changes.

## Publishing

- GitHub Pages publishes from `main:/docs` at the public URL above.
- Rebuild `docs/` with `npm run build:pages` before committing a Pages release.
- The secondary hosted version uses the existing Sites project in `.openai/hosting.json`.
- Do not rename the repository, Pages base path, or hosted slug unless explicitly requested.

