# Giggle Zoo!

A playful browser-based webcam game where kids meet a reactive animal twin.

**Play it:** https://kbo4sho.github.io/mugshot-menagerie/

## What it does

- Tracks up to six faces at once
- Draws 92 original rendered animal masks directly on a canvas
- Follows face position, scale, and head tilt
- Reacts to blinking, smiling, and opening your mouth
- Keeps animal assignments stable until you shuffle
- Supports button, touch, and Space-key controls
- Includes a full-screen zoo camera mode
- Stops and releases the camera explicitly

## Privacy

Camera frames stay in the browser. The app does not record, store, or upload photos or video. The MediaPipe browser runtime and face model are downloaded when the camera starts, then face landmark detection runs on-device.

## Run locally

Requires Node.js 22.13 or newer.

```bash
npm install
npm run dev
```

Then open the local URL shown in the terminal and allow camera access.

## Build

```bash
npm run build
```

## Built with

- React
- TypeScript
- MediaPipe Face Landmarker
- Canvas 2D
- vinext

Camera access requires a secure context: use `localhost` during development or HTTPS when deployed.
