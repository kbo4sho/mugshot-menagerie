"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  FaceLandmarker,
  FilesetResolver,
  type FaceLandmarkerResult,
  type NormalizedLandmark,
} from "@mediapipe/tasks-vision";
import { blendRenderedMaskRgba, getRenderedMaskBlendWeights } from "./rendered-mask-blend.mjs";

type CameraState = "idle" | "requesting" | "warming" | "live" | "error" | "off";

type Animal = {
  id: string;
  name: string;
  color: string;
  accent: string;
  dark: string;
};

type Pose = {
  x: number;
  y: number;
  scale: number;
  angle: number;
  blinkLeft: number;
  blinkRight: number;
  mouth: number;
  smile: number;
};

type FaceTrack = {
  id: number;
  animal: number;
  pose: Pose;
  lastSeen: number;
};

type Particle = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  born: number;
  color: string;
  spin: number;
};

type RenderedMaskState = "neutral" | "blink" | "roar";
type RenderedMaskSources = Record<RenderedMaskState, string> & { roarMid?: string };

const ANIMAL_ROSTER: Animal[] = [
  { id: "capybara", name: "Bubblegum Capybara", color: "#B97745", accent: "#FFD166", dark: "#4A2A20" },
  { id: "frog", name: "Disco Frog", color: "#8BD450", accent: "#F4FF74", dark: "#213C25" },
  { id: "pigeon", name: "Party Pigeon", color: "#8E9DF4", accent: "#54E0C7", dark: "#28345C" },
  { id: "raccoon", name: "Raccoon Rascal", color: "#A9A8B5", accent: "#F1F0EA", dark: "#2C2B3A" },
  { id: "axolotl", name: "Happy Axolotl", color: "#FF91B8", accent: "#FFD3E3", dark: "#71334F" },
  { id: "cow", name: "Moo-Moo Superstar", color: "#FFF2CF", accent: "#FE6F5E", dark: "#3B2B29" },
  { id: "llama", name: "Drama Llama", color: "#E8B5FF", accent: "#FFF1BE", dark: "#57356C" },
  { id: "otter", name: "Singing Otter", color: "#8A6248", accent: "#E8BD80", dark: "#35251F" },
  { id: "tiger", name: "Tiny Tiger", color: "#FF9D3D", accent: "#FFE2A1", dark: "#512D20" },
  { id: "goat", name: "Bouncy Goat", color: "#C9E5E2", accent: "#F7FFFB", dark: "#344A4A" },
  { id: "panda", name: "Pancake Panda", color: "#F8F0DA", accent: "#FFFDF4", dark: "#292A36" },
  { id: "elephant", name: "Trumpet Elephant", color: "#92AFC0", accent: "#F4A7B9", dark: "#354552" },
  { id: "lion", name: "Sunshine Lion", color: "#F3B64B", accent: "#FFE08A", dark: "#9A532B" },
  { id: "giraffe", name: "Jolly Giraffe", color: "#F7C95D", accent: "#FFF2B2", dark: "#9A6236" },
  { id: "monkey", name: "Banana Monkey", color: "#9A694E", accent: "#F2C38E", dark: "#442B24" },
  { id: "koala", name: "Cuddle Koala", color: "#A8B6C1", accent: "#F7D0D7", dark: "#394854" },
  { id: "hippo", name: "Bubble Hippo", color: "#9A87C5", accent: "#E8B7D5", dark: "#3F345D" },
  { id: "zebra", name: "Zigzag Zebra", color: "#F3F0E5", accent: "#8FD3C7", dark: "#262638" },
  { id: "fox", name: "Fantastic Fox", color: "#F47D42", accent: "#FFF0D2", dark: "#503026" },
  { id: "bunny", name: "Hopscotch Bunny", color: "#D9C1F0", accent: "#FFB9D2", dark: "#493956" },
  { id: "pig", name: "Puddle Pig", color: "#F5A8B8", accent: "#FFD1D7", dark: "#7A3E52" },
  { id: "dog", name: "Wiggle Puppy", color: "#C88955", accent: "#F7E0B5", dark: "#513528" },
  { id: "cat", name: "Curious Cat", color: "#AFA4E8", accent: "#FFD38E", dark: "#3D365D" },
  { id: "owl", name: "Hoot-Hoot Owl", color: "#8B6F5A", accent: "#F8E5B6", dark: "#362B27" },
  { id: "penguin", name: "Waddles Penguin", color: "#3C465D", accent: "#FFF7DE", dark: "#222735" },
  { id: "sloth", name: "Sleepy Sloth", color: "#9C8065", accent: "#E5C7A1", dark: "#4A382E" },
  { id: "bear", name: "Honey Bear", color: "#B47B4E", accent: "#F2C68D", dark: "#4D3024" },
  { id: "deer", name: "Twinkle Deer", color: "#B98257", accent: "#F4D5AA", dark: "#493127" },
  { id: "flamingo", name: "Fancy Flamingo", color: "#F58BAA", accent: "#FFD4DD", dark: "#5A3041" },
  { id: "parrot", name: "Pirate Parrot", color: "#45B982", accent: "#FFE55C", dark: "#28493D" },
  { id: "shark", name: "Super Shark", color: "#6FA7BD", accent: "#DDF5F7", dark: "#273F52" },
  { id: "octopus", name: "Disco Octopus", color: "#9C77D9", accent: "#F3B1E5", dark: "#433059" },
  { id: "chameleon", name: "Color-Pop Chameleon", color: "#78C76B", accent: "#E8E85D", dark: "#2D573A" },
  { id: "unicorn", name: "Sparkle Unicorn", color: "#F5ECFF", accent: "#FFB9DF", dark: "#745A94" },
  { id: "crocodile", name: "Grinning Crocodile", color: "#78A94B", accent: "#D4E67C", dark: "#304C2A" },
  { id: "kangaroo", name: "Boing-Boing Kangaroo", color: "#C88755", accent: "#F2C28D", dark: "#513526" },
  { id: "rhino", name: "Rumble Rhino", color: "#8D9AA0", accent: "#D6D3C5", dark: "#39454B" },
  { id: "gorilla", name: "Groove Gorilla", color: "#52505E", accent: "#A28D82", dark: "#252530" },
  { id: "lemur", name: "Ringtail Lemur", color: "#A9A6B0", accent: "#F7F1DF", dark: "#353542" },
  { id: "meerkat", name: "Peekaboo Meerkat", color: "#C99B61", accent: "#F4D4A0", dark: "#4B3826" },
  { id: "redpanda", name: "Red Panda Rocket", color: "#C85F3D", accent: "#FFF0D7", dark: "#4A2D28" },
  { id: "leopard", name: "Polka-Dot Leopard", color: "#E8B84F", accent: "#F8E6A0", dark: "#3D2D24" },
  { id: "cheetah", name: "Zoom-Zoom Cheetah", color: "#F0C35C", accent: "#FFF0B0", dark: "#3D3126" },
  { id: "wolf", name: "Moonlight Wolf", color: "#7B8798", accent: "#DCE3E8", dark: "#2E3442" },
  { id: "moose", name: "Mighty Moose", color: "#8B5D43", accent: "#C9976D", dark: "#3D2A22" },
  { id: "ram", name: "Rock-Star Ram", color: "#B7A48F", accent: "#F0DEC5", dark: "#493E34" },
  { id: "alpaca", name: "Fluffy Alpaca", color: "#F2D8B9", accent: "#FFF4E1", dark: "#6A4C3C" },
  { id: "toucan", name: "Topsy Toucan", color: "#303645", accent: "#FFD84D", dark: "#1D2130" },
  { id: "peacock", name: "Proud Peacock", color: "#2E9A8A", accent: "#5FE0C0", dark: "#28385A" },
  { id: "pelican", name: "Scoop Pelican", color: "#F4E2C0", accent: "#FFB65D", dark: "#574738" },
  { id: "eagle", name: "Sky-High Eagle", color: "#8B603F", accent: "#F5F0DD", dark: "#38271F" },
  { id: "bat", name: "Boogie Bat", color: "#6D5B83", accent: "#BCA6D6", dark: "#30283F" },
  { id: "seal", name: "Splashy Seal", color: "#7D9EA8", accent: "#D8EFF0", dark: "#314A52" },
  { id: "dolphin", name: "Daring Dolphin", color: "#559DC4", accent: "#CDEFFC", dark: "#24495E" },
  { id: "whale", name: "Wavy Whale", color: "#506FA5", accent: "#C9E0F4", dark: "#293950" },
  { id: "crab", name: "Click-Clack Crab", color: "#EF6B52", accent: "#FFB18F", dark: "#623027" },
  { id: "jellyfish", name: "Jiggly Jellyfish", color: "#8F79D6", accent: "#F0C1F5", dark: "#42345D" },
  { id: "turtle", name: "Turbo Turtle", color: "#62A76F", accent: "#B9D66E", dark: "#2F5135" },
  { id: "snake", name: "Sneaky Snake", color: "#73A84C", accent: "#E6D75B", dark: "#304926" },
  { id: "armadillo", name: "Roll-Up Armadillo", color: "#A27D68", accent: "#D6B49C", dark: "#46352E" },
  { id: "walrus", name: "Sir Splish Walrus", color: "#9B766D", accent: "#E8BEA7", dark: "#463139" },
  { id: "orangutan", name: "Swingy Orangutan", color: "#C65F32", accent: "#F3B67E", dark: "#542A24" },
  { id: "baboon", name: "Bongo Baboon", color: "#8B6966", accent: "#68BFD0", dark: "#382C39" },
  { id: "platypus", name: "Paddle-Pop Platypus", color: "#8B604B", accent: "#E9A54E", dark: "#3B2B29" },
  { id: "anteater", name: "Noodle-Nose Anteater", color: "#9A8C7B", accent: "#E8D6B8", dark: "#3D3532" },
  { id: "tapir", name: "Tippy Tapir", color: "#514A57", accent: "#D9B3A8", dark: "#242330" },
  { id: "okapi", name: "Stripe-Socks Okapi", color: "#7B4C3C", accent: "#F5E9D3", dark: "#342727" },
  { id: "hyena", name: "Cackle Hyena", color: "#C49A55", accent: "#F3D897", dark: "#49372A" },
  { id: "warthog", name: "Wiggle-Tusk Warthog", color: "#826D67", accent: "#D3A884", dark: "#382E31" },
  { id: "buffalo", name: "Booming Buffalo", color: "#584239", accent: "#CDAE7C", dark: "#262126" },
  { id: "camel", name: "Wobble Camel", color: "#D19B5B", accent: "#F2D095", dark: "#523B2A" },
  { id: "porcupine", name: "Pokey-Pop Porcupine", color: "#735847", accent: "#E3C58F", dark: "#342922" },
  { id: "skunk", name: "Stinky-Winky Skunk", color: "#353641", accent: "#FFF8E5", dark: "#1E1F29" },
  { id: "beaver", name: "Chomper Beaver", color: "#8E5C3E", accent: "#E4B37C", dark: "#3A2924" },
  { id: "hedgehog", name: "Prickle-Giggle Hedgehog", color: "#9B704D", accent: "#EBC48E", dark: "#443126" },
  { id: "rooster", name: "Rock-and-Roll Rooster", color: "#F3E5C0", accent: "#EF534D", dark: "#3D3041" },
  { id: "turkey", name: "Gobble-Wobble Turkey", color: "#8B573E", accent: "#E35D4F", dark: "#3B2925" },
  { id: "puffin", name: "Puzzle-Beak Puffin", color: "#313845", accent: "#FFF3D5", dark: "#20232D" },
  { id: "cockatoo", name: "Party-Crest Cockatoo", color: "#FFF0B8", accent: "#FFD74E", dark: "#40384B" },
  { id: "ostrich", name: "Tiptoe Ostrich", color: "#D8A7A4", accent: "#F7D9CE", dark: "#49343A" },
  { id: "squid", name: "Squeezy Squid", color: "#A879D5", accent: "#F2B8E5", dark: "#41304F" },
  { id: "lobster", name: "Clickity Lobster", color: "#E85E45", accent: "#FFB274", dark: "#5A2B28" },
  { id: "seahorse", name: "Curly Seahorse", color: "#E6A84D", accent: "#FFF08C", dark: "#4B3B31" },
  { id: "stingray", name: "Flapjack Stingray", color: "#6F8FA8", accent: "#C8EDF1", dark: "#2D3C4B" },
  { id: "pufferfish", name: "Poppy Pufferfish", color: "#E6B84E", accent: "#FFF3A2", dark: "#493B2C" },
  { id: "horse", name: "Galloping Glitter Horse", color: "#B9784D", accent: "#F3C98B", dark: "#4B3027" },
  { id: "donkey", name: "Hee-Haw Donkey", color: "#8B8D96", accent: "#D9C5B2", dark: "#353640" },
  { id: "sheep", name: "Baa-Baa Bounce Sheep", color: "#F2E9D5", accent: "#E9B7C2", dark: "#514A48" },
  { id: "squirrel", name: "Acorn Acrobat Squirrel", color: "#B96F3F", accent: "#F0B875", dark: "#4A2E25" },
  { id: "mouse", name: "Teeny-Twinkle Mouse", color: "#A9A5B5", accent: "#F5B8C8", dark: "#3D3948" },
  { id: "hamster", name: "Cheeky Hamster", color: "#D99957", accent: "#FFF0CF", dark: "#563A2C" },
  { id: "duck", name: "Quack Attack Duck", color: "#F2D34F", accent: "#FF9E45", dark: "#4D4126" },
  { id: "goose", name: "Goose on the Loose", color: "#F2F0E4", accent: "#F0A54B", dark: "#414653" },
  { id: "swan", name: "Swirly Swan", color: "#FFF9EB", accent: "#F2A8B7", dark: "#3D4050" },
  { id: "crow", name: "Clever-Cackle Crow", color: "#394052", accent: "#747FA6", dark: "#1D2230" },
  { id: "bumblebee", name: "Buzzy Bumblebee", color: "#F5C84B", accent: "#FFF1A1", dark: "#3D332B" },
  { id: "butterfly", name: "Flutter-By Butterfly", color: "#A879E6", accent: "#FFB7D5", dark: "#49335F" },
  { id: "ladybug", name: "Lucky Ladybug", color: "#EE594F", accent: "#FFAAA0", dark: "#3A292E" },
  { id: "mantis", name: "Mighty Mantis", color: "#78BD52", accent: "#D8EE78", dark: "#315036" },
  { id: "snail", name: "Silly-Swirl Snail", color: "#8BCB8C", accent: "#F2A66F", dark: "#3B513C" },
];

const CONFETTI = ["#FF5B45", "#F8E542", "#64E0B8", "#9E82FF", "#FF8BC2"];

const RENDERED_MASK_VERSIONS: Record<string, string> = {
  axolotl: "v2",
  bear: "v1",
  bumblebee: "v1",
  bunny: "v2",
  capybara: "v2",
  cat: "v1",
  chameleon: "v2",
  cow: "v2",
  crocodile: "v1",
  deer: "v1",
  dog: "v1",
  elephant: "v2",
  flamingo: "v1",
  fox: "v1",
  frog: "v1",
  giraffe: "v1",
  goat: "v1",
  gorilla: "v2",
  hippo: "v1",
  kangaroo: "v9",
  koala: "v1",
  lemur: "v7",
  lion: "v1",
  llama: "v1",
  meerkat: "v1",
  monkey: "v1",
  octopus: "v1",
  otter: "v2",
  owl: "v1",
  panda: "v2",
  parrot: "v3",
  pigeon: "v2",
  pig: "v1",
  penguin: "v2",
  raccoon: "v1",
  redpanda: "v1",
  leopard: "v1",
  cheetah: "v1",
  rhino: "v2",
  shark: "v2",
  sloth: "v5",
  tiger: "v3",
  unicorn: "v2",
  zebra: "v1",
  wolf: "v1",
  moose: "v1",
  ram: "v1",
  alpaca: "v1",
  toucan: "v1",
  peacock: "v1",
};

const ANIMALS: Animal[] = ANIMAL_ROSTER.filter((animal) => animal.id in RENDERED_MASK_VERSIONS);

const RENDERED_MASK_ROAR_MID_VERSIONS: Partial<Record<string, string>> = {
  chameleon: "v2",
  gorilla: "v2",
  kangaroo: "v9",
  lemur: "v7",
  rhino: "v2",
  sloth: "v5",
};

const RENDERED_MASK_IDS = Object.keys(RENDERED_MASK_VERSIONS);

const RENDERED_MASK_SOURCES: Partial<Record<string, RenderedMaskSources>> = Object.fromEntries(
  Object.entries(RENDERED_MASK_VERSIONS).map(([id, version]) => {
    const roarMidVersion = RENDERED_MASK_ROAR_MID_VERSIONS[id];
    return [id, {
      neutral: `./masks/${id}/neutral-${version}.webp`,
      blink: `./masks/${id}/blink-${version}.webp`,
      roar: `./masks/${id}/roar-${version}.webp`,
      ...(roarMidVersion ? { roarMid: `./masks/${id}/roar-mid-${roarMidVersion}.webp` } : {}),
    }];
  }),
);

const renderedMaskImages = new Map<string, HTMLImageElement>();
const renderedMaskPixels = new Map<string, Uint8ClampedArray>();
let renderedMaskBlendCanvas: HTMLCanvasElement | null = null;
let renderedMaskDecodeCanvas: HTMLCanvasElement | null = null;
let renderedMaskOutput: ImageData | null = null;

function getRenderedMaskBlendSurface(size: number) {
  if (typeof document === "undefined") return null;
  if (!renderedMaskBlendCanvas) renderedMaskBlendCanvas = document.createElement("canvas");
  if (renderedMaskBlendCanvas.width !== size || renderedMaskBlendCanvas.height !== size) {
    renderedMaskBlendCanvas.width = size;
    renderedMaskBlendCanvas.height = size;
    renderedMaskOutput = null;
  }
  const context = renderedMaskBlendCanvas.getContext("2d");
  if (context) context.imageSmoothingQuality = "high";
  return context ? { canvas: renderedMaskBlendCanvas, context } : null;
}

function getRenderedMaskPixels(image: HTMLImageElement, size: number) {
  const key = `${image.src}@${size}`;
  const cached = renderedMaskPixels.get(key);
  if (cached) return cached;
  if (typeof document === "undefined" || !image.complete || image.naturalWidth <= 0) return null;
  if (!renderedMaskDecodeCanvas) renderedMaskDecodeCanvas = document.createElement("canvas");
  if (renderedMaskDecodeCanvas.width !== size || renderedMaskDecodeCanvas.height !== size) {
    renderedMaskDecodeCanvas.width = size;
    renderedMaskDecodeCanvas.height = size;
  }
  const context = renderedMaskDecodeCanvas.getContext("2d");
  if (!context) return null;
  context.clearRect(0, 0, size, size);
  context.drawImage(image, 0, 0, size, size);
  const pixels = context.getImageData(0, 0, size, size).data;
  renderedMaskPixels.set(key, pixels);
  return pixels;
}

function loadRenderedMask(src: string) {
  if (typeof window === "undefined") return null;
  const cached = renderedMaskImages.get(src);
  if (cached) return cached;
  const image = new window.Image();
  image.decoding = "async";
  image.src = src;
  renderedMaskImages.set(src, image);
  return image;
}

function preloadRenderedMask(animalId: string) {
  const states = RENDERED_MASK_SOURCES[animalId];
  if (!states) return [];
  return Object.values(states).map(loadRenderedMask).filter((image): image is HTMLImageElement => Boolean(image));
}

function preloadRenderedMasks() {
  return RENDERED_MASK_IDS.flatMap(preloadRenderedMask);
}

const clamp = (value: number, min = 0, max = 1) => Math.max(min, Math.min(max, value));
const mix = (from: number, to: number, amount: number) => from + (to - from) * amount;

function categoryScore(result: FaceLandmarkerResult, face: number, name: string) {
  const categories = result.faceBlendshapes?.[face]?.categories ?? [];
  return categories.find((item) => item.categoryName === name)?.score ?? 0;
}

function randomAnimal(except?: number) {
  let pick = Math.floor(Math.random() * ANIMALS.length);
  if (except !== undefined && ANIMALS.length > 1) {
    while (pick === except) pick = Math.floor(Math.random() * ANIMALS.length);
  }
  return pick;
}

function ellipse(ctx: CanvasRenderingContext2D, x: number, y: number, rx: number, ry: number, fill: string) {
  ctx.beginPath();
  ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
}

function strokeEllipse(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  rx: number,
  ry: number,
  stroke: string,
  lineWidth: number,
) {
  ctx.beginPath();
  ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  ctx.strokeStyle = stroke;
  ctx.lineWidth = lineWidth;
  ctx.stroke();
}

function triangle(
  ctx: CanvasRenderingContext2D,
  points: [number, number][],
  fill: string,
) {
  ctx.beginPath();
  ctx.moveTo(points[0][0], points[0][1]);
  points.slice(1).forEach(([x, y]) => ctx.lineTo(x, y));
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
}

function drawEye(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  blink: number,
  pupil: string,
  surprised: number,
) {
  const height = Math.max(3, 22 * (1 - blink * 0.9) + surprised * 5);
  ellipse(ctx, x, y, 25, height, "#FFFDF4");
  strokeEllipse(ctx, x, y, 25, height, pupil, 4);
  if (height > 7) {
    ellipse(ctx, x + 2, y + 2, 9 + surprised * 2, 11 + surprised * 3, pupil);
    ellipse(ctx, x + 5, y - 2, 3, 3, "#FFFDF4");
  } else {
    ctx.beginPath();
    ctx.moveTo(x - 17, y);
    ctx.quadraticCurveTo(x, y + 7, x + 17, y);
    ctx.strokeStyle = pupil;
    ctx.lineWidth = 5;
    ctx.lineCap = "round";
    ctx.stroke();
  }
}

function drawBumblebeeEye(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  blink: number,
  surprised: number,
  dark: string,
) {
  const height = Math.max(3, 34 * (1 - blink * .94) + surprised * 8);

  if (height <= 7) {
    ctx.beginPath();
    ctx.moveTo(x - 27, y);
    ctx.quadraticCurveTo(x, y + 11, x + 27, y);
    ctx.strokeStyle = dark;
    ctx.lineWidth = 7;
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x - 18, y - 4); ctx.lineTo(x - 25, y - 9);
    ctx.moveTo(x + 18, y - 4); ctx.lineTo(x + 25, y - 9);
    ctx.lineWidth = 4;
    ctx.stroke();
    return;
  }

  ellipse(ctx, x, y, 36, height, "#FFFBEA");
  strokeEllipse(ctx, x, y, 36, height, dark, 5);
  ellipse(ctx, x, y + 3, 17 + surprised * 2, 21 + surprised * 4, "#DB8B2C");
  ellipse(ctx, x, y + 5, 9 + surprised * 2, 14 + surprised * 3, dark);
  ellipse(ctx, x - 6, y - 7, 6, 7, "#FFFDF4");
  ellipse(ctx, x + 5, y + 2, 2.5, 3, "rgba(255,255,255,.72)");

  ctx.beginPath();
  ctx.moveTo(x - 26, y - height - 8 - surprised * 4);
  ctx.quadraticCurveTo(x, y - height - 16 - surprised * 7, x + 26, y - height - 8 - surprised * 4);
  ctx.strokeStyle = dark;
  ctx.lineWidth = 6;
  ctx.stroke();
}

function drawMouth(ctx: CanvasRenderingContext2D, animal: Animal, pose: Pose, y = 69) {
  const open = clamp((pose.mouth - 0.08) * 1.55);
  if (open > 0.06) {
    ellipse(ctx, 0, y + open * 8, 28 + open * 9, 7 + open * 29, animal.dark);
    if (open > 0.34) ellipse(ctx, 0, y + 16 + open * 15, 18, 7 + open * 4, "#FF7598");
    if (open > 0.64) {
      ctx.fillStyle = "#FFF8DD";
      ctx.fillRect(-20, y - 1, 40, 7);
    }
  } else {
    ctx.beginPath();
    ctx.moveTo(-26, y);
    ctx.quadraticCurveTo(0, y + 8 + pose.smile * 12, 26, y);
    ctx.strokeStyle = animal.dark;
    ctx.lineWidth = 6;
    ctx.lineCap = "round";
    ctx.stroke();
  }
}

function drawExtraBack(ctx: CanvasRenderingContext2D, animal: Animal) {
  switch (animal.id) {
    case "panda":
      ellipse(ctx, -94, -98, 42, 46, animal.dark);
      ellipse(ctx, 94, -98, 42, 46, animal.dark);
      ellipse(ctx, -94, -98, 20, 23, animal.accent);
      ellipse(ctx, 94, -98, 20, 23, animal.accent);
      break;
    case "elephant":
      ellipse(ctx, -120, -8, 76, 108, animal.color);
      ellipse(ctx, 120, -8, 76, 108, animal.color);
      ellipse(ctx, -124, -4, 48, 78, animal.accent);
      ellipse(ctx, 124, -4, 48, 78, animal.accent);
      break;
    case "lion":
      for (let i = 0; i < 12; i += 1) {
        const angle = (i / 12) * Math.PI * 2;
        ellipse(ctx, Math.cos(angle) * 122, Math.sin(angle) * 134 - 5, 47, 52, animal.dark);
      }
      break;
    case "giraffe":
      triangle(ctx, [[-83, -91], [-137, -125], [-108, -55]], animal.color);
      triangle(ctx, [[83, -91], [137, -125], [108, -55]], animal.color);
      ctx.strokeStyle = animal.dark;
      ctx.lineWidth = 14;
      ctx.beginPath();
      ctx.moveTo(-52, -108); ctx.lineTo(-61, -158);
      ctx.moveTo(52, -108); ctx.lineTo(61, -158);
      ctx.stroke();
      ellipse(ctx, -62, -161, 19, 16, animal.dark);
      ellipse(ctx, 62, -161, 19, 16, animal.dark);
      break;
    case "monkey":
      ellipse(ctx, -119, -12, 58, 70, animal.dark);
      ellipse(ctx, 119, -12, 58, 70, animal.dark);
      ellipse(ctx, -119, -12, 36, 47, animal.accent);
      ellipse(ctx, 119, -12, 36, 47, animal.accent);
      break;
    case "koala":
      [-1, 1].forEach((side) => {
        ellipse(ctx, side * 108, -72, 55, 61, animal.color);
        ellipse(ctx, side * 108, -72, 33, 38, animal.accent);
        for (let i = 0; i < 6; i += 1) {
          const angle = (i / 6) * Math.PI * 2;
          ellipse(ctx, side * 108 + Math.cos(angle) * 35, -72 + Math.sin(angle) * 39, 18, 20, animal.color);
        }
      });
      break;
    case "hippo":
      ellipse(ctx, -87, -105, 28, 34, animal.dark);
      ellipse(ctx, 87, -105, 28, 34, animal.dark);
      ellipse(ctx, -87, -105, 14, 18, animal.accent);
      ellipse(ctx, 87, -105, 14, 18, animal.accent);
      break;
    case "zebra":
      triangle(ctx, [[-80, -85], [-119, -145], [-38, -112]], animal.color);
      triangle(ctx, [[80, -85], [119, -145], [38, -112]], animal.color);
      triangle(ctx, [[-78, -94], [-108, -133], [-49, -112]], animal.accent);
      triangle(ctx, [[78, -94], [108, -133], [49, -112]], animal.accent);
      break;
    case "fox":
      triangle(ctx, [[-84, -73], [-132, -157], [-28, -111]], animal.color);
      triangle(ctx, [[84, -73], [132, -157], [28, -111]], animal.color);
      triangle(ctx, [[-84, -88], [-119, -139], [-46, -111]], animal.dark);
      triangle(ctx, [[84, -88], [119, -139], [46, -111]], animal.dark);
      break;
    case "bunny":
      ellipse(ctx, -59, -141, 31, 82, animal.color);
      ellipse(ctx, 59, -141, 31, 82, animal.color);
      ellipse(ctx, -59, -143, 13, 59, animal.accent);
      ellipse(ctx, 59, -143, 13, 59, animal.accent);
      break;
    case "pig":
      triangle(ctx, [[-79, -83], [-136, -115], [-105, -34]], animal.color);
      triangle(ctx, [[79, -83], [136, -115], [105, -34]], animal.color);
      triangle(ctx, [[-84, -85], [-123, -106], [-104, -55]], animal.accent);
      triangle(ctx, [[84, -85], [123, -106], [104, -55]], animal.accent);
      break;
    case "dog":
      ctx.save();
      ctx.translate(-109, -48); ctx.rotate(0.38);
      ellipse(ctx, -10, 16, 42, 79, animal.dark);
      ctx.restore();
      ctx.save();
      ctx.translate(109, -48); ctx.rotate(-0.38);
      ellipse(ctx, 10, 16, 42, 79, animal.dark);
      ctx.restore();
      break;
    case "cat":
      triangle(ctx, [[-82, -73], [-125, -150], [-25, -111]], animal.color);
      triangle(ctx, [[82, -73], [125, -150], [25, -111]], animal.color);
      triangle(ctx, [[-82, -88], [-113, -135], [-48, -110]], animal.accent);
      triangle(ctx, [[82, -88], [113, -135], [48, -110]], animal.accent);
      break;
    case "owl":
      triangle(ctx, [[-83, -77], [-127, -141], [-25, -105]], animal.dark);
      triangle(ctx, [[83, -77], [127, -141], [25, -105]], animal.dark);
      break;
    case "penguin":
      triangle(ctx, [[-92, 8], [-148, 66], [-105, 79]], animal.dark);
      triangle(ctx, [[92, 8], [148, 66], [105, 79]], animal.dark);
      break;
    case "sloth":
      ellipse(ctx, -94, -90, 35, 42, animal.dark);
      ellipse(ctx, 94, -90, 35, 42, animal.dark);
      break;
    case "bear":
      ellipse(ctx, -94, -94, 39, 43, animal.dark);
      ellipse(ctx, 94, -94, 39, 43, animal.dark);
      ellipse(ctx, -94, -94, 20, 22, animal.accent);
      ellipse(ctx, 94, -94, 20, 22, animal.accent);
      break;
    case "deer":
      triangle(ctx, [[-84, -87], [-139, -116], [-104, -49]], animal.color);
      triangle(ctx, [[84, -87], [139, -116], [104, -49]], animal.color);
      ctx.strokeStyle = animal.dark;
      ctx.lineWidth = 11;
      ctx.beginPath();
      ctx.moveTo(-61, -104); ctx.lineTo(-86, -157); ctx.lineTo(-112, -174);
      ctx.moveTo(-84, -150); ctx.lineTo(-64, -176);
      ctx.moveTo(61, -104); ctx.lineTo(86, -157); ctx.lineTo(112, -174);
      ctx.moveTo(84, -150); ctx.lineTo(64, -176);
      ctx.stroke();
      break;
    case "flamingo":
      [-1, 0, 1].forEach((offset) => {
        ctx.save();
        ctx.translate(offset * 25, -126 + Math.abs(offset) * 9);
        ctx.rotate(offset * 0.28);
        ellipse(ctx, 0, -8, 19, 49, offset === 0 ? animal.accent : animal.color);
        ctx.restore();
      });
      break;
    case "parrot":
      [-1, 0, 1].forEach((offset) => {
        ctx.save();
        ctx.translate(offset * 24, -126 + Math.abs(offset) * 10);
        ctx.rotate(offset * 0.36);
        ellipse(ctx, 0, -12, 18, 54, offset === 0 ? "#FF6B5F" : animal.accent);
        ctx.restore();
      });
      break;
    case "shark":
      triangle(ctx, [[0, -91], [-12, -170], [54, -105]], animal.dark);
      triangle(ctx, [[-96, 18], [-157, 63], [-105, 77]], animal.color);
      triangle(ctx, [[96, 18], [157, 63], [105, 77]], animal.color);
      break;
    case "octopus":
      [-108, -69, -28, 28, 69, 108].forEach((x, index) => {
        ellipse(ctx, x, 92 + (index % 2) * 16, 34, 73, index % 2 ? animal.accent : animal.color);
      });
      break;
    case "chameleon":
      [-78, -39, 0, 39, 78].forEach((x, index) => {
        triangle(ctx, [[x - 21, -103], [x, -155 - Math.abs(index - 2) * 3], [x + 21, -103]], index % 2 ? animal.accent : animal.dark);
      });
      break;
    case "unicorn":
      triangle(ctx, [[-83, -78], [-124, -143], [-27, -108]], animal.color);
      triangle(ctx, [[83, -78], [124, -143], [27, -108]], animal.color);
      triangle(ctx, [[-19, -101], [0, -190], [19, -101]], animal.accent);
      ctx.strokeStyle = animal.dark;
      ctx.lineWidth = 5;
      ctx.beginPath();
      ctx.moveTo(-12, -122); ctx.lineTo(9, -169);
      ctx.moveTo(-5, -148); ctx.lineTo(14, -151);
      ctx.stroke();
      break;
    case "crocodile":
      [-82, -41, 0, 41, 82].forEach((x, index) => {
        triangle(ctx, [[x - 22, -102], [x, -146 - Math.abs(index - 2) * 2], [x + 22, -102]], animal.dark);
      });
      break;
    case "kangaroo":
      [-1, 1].forEach((side) => {
        ctx.save(); ctx.translate(side * 58, -151); ctx.rotate(side * .16);
        ellipse(ctx, 0, 0, 27, 78, animal.color); ellipse(ctx, 0, -3, 11, 56, animal.accent); ctx.restore();
      });
      break;
    case "rhino":
      ellipse(ctx, -100, -83, 36, 45, animal.color); ellipse(ctx, 100, -83, 36, 45, animal.color);
      ellipse(ctx, -100, -83, 17, 24, animal.accent); ellipse(ctx, 100, -83, 17, 24, animal.accent);
      triangle(ctx, [[-19, -103], [0, -183], [20, -103]], animal.accent);
      break;
    case "gorilla":
      ellipse(ctx, -116, -24, 61, 76, animal.dark); ellipse(ctx, 116, -24, 61, 76, animal.dark);
      ellipse(ctx, -119, -20, 36, 48, animal.accent); ellipse(ctx, 119, -20, 36, 48, animal.accent);
      break;
    case "lemur":
      ellipse(ctx, -99, -90, 40, 49, animal.dark); ellipse(ctx, 99, -90, 40, 49, animal.dark);
      ellipse(ctx, -99, -90, 22, 29, animal.accent); ellipse(ctx, 99, -90, 22, 29, animal.accent);
      break;
    case "meerkat":
      ellipse(ctx, -82, -107, 28, 35, animal.dark); ellipse(ctx, 82, -107, 28, 35, animal.dark);
      ellipse(ctx, -82, -107, 13, 18, animal.accent); ellipse(ctx, 82, -107, 13, 18, animal.accent);
      break;
    case "redpanda":
      triangle(ctx, [[-83, -76], [-127, -142], [-28, -108]], animal.dark);
      triangle(ctx, [[83, -76], [127, -142], [28, -108]], animal.dark);
      triangle(ctx, [[-81, -91], [-114, -128], [-49, -108]], animal.accent);
      triangle(ctx, [[81, -91], [114, -128], [49, -108]], animal.accent);
      break;
    case "leopard":
    case "cheetah":
      ellipse(ctx, -91, -101, 35, 40, animal.color); ellipse(ctx, 91, -101, 35, 40, animal.color);
      ellipse(ctx, -91, -101, 17, 21, animal.accent); ellipse(ctx, 91, -101, 17, 21, animal.accent);
      break;
    case "wolf":
      triangle(ctx, [[-83, -72], [-127, -157], [-27, -109]], animal.color);
      triangle(ctx, [[83, -72], [127, -157], [27, -109]], animal.color);
      triangle(ctx, [[-82, -88], [-115, -138], [-47, -109]], animal.accent);
      triangle(ctx, [[82, -88], [115, -138], [47, -109]], animal.accent);
      break;
    case "moose":
      [-1, 1].forEach((side) => {
        ctx.strokeStyle = animal.dark; ctx.lineWidth = 18; ctx.beginPath();
        ctx.moveTo(side * 66, -103); ctx.lineTo(side * 91, -153); ctx.lineTo(side * 122, -178);
        ctx.moveTo(side * 90, -147); ctx.lineTo(side * 68, -180);
        ctx.moveTo(side * 106, -163); ctx.lineTo(side * 139, -153); ctx.stroke();
        ellipse(ctx, side * 104, -166, 21, 31, animal.dark);
        ellipse(ctx, side * 102, -83, 35, 45, animal.color);
      });
      break;
    case "ram":
      [-1, 1].forEach((side) => {
        strokeEllipse(ctx, side * 96, -75, 48, 55, animal.accent, 22);
        ellipse(ctx, side * 101, -76, 19, 25, animal.dark);
      });
      break;
    case "alpaca":
      ellipse(ctx, -66, -150, 29, 72, animal.color); ellipse(ctx, 66, -150, 29, 72, animal.color);
      ellipse(ctx, -66, -152, 12, 51, animal.accent); ellipse(ctx, 66, -152, 12, 51, animal.accent);
      [-76, -39, 0, 39, 76].forEach((x) => ellipse(ctx, x, -119, 32, 34, animal.accent));
      break;
    case "toucan":
      [-2, -1, 0, 1, 2].forEach((offset) => {
        ctx.save(); ctx.translate(offset * 20, -126 + Math.abs(offset) * 10); ctx.rotate(offset * .28);
        ellipse(ctx, 0, -10, 16, 48, offset % 2 ? animal.accent : animal.color); ctx.restore();
      });
      break;
    case "peacock":
      for (let i = 0; i < 9; i += 1) {
        const angle = Math.PI + (i / 8) * Math.PI;
        const x = Math.cos(angle) * 116; const y = Math.sin(angle) * 104 - 32;
        ellipse(ctx, x, y, 34, 53, i % 2 ? animal.color : animal.accent);
        ellipse(ctx, x, y - 8, 13, 22, animal.dark);
      }
      break;
    case "pelican":
      triangle(ctx, [[-91, 5], [-151, 63], [-101, 78]], animal.accent);
      triangle(ctx, [[91, 5], [151, 63], [101, 78]], animal.accent);
      [-1, 0, 1].forEach((offset) => ellipse(ctx, offset * 24, -130 + Math.abs(offset) * 9, 18, 48, animal.color));
      break;
    case "eagle":
      triangle(ctx, [[-92, -5], [-158, 48], [-105, 69]], animal.dark);
      triangle(ctx, [[92, -5], [158, 48], [105, 69]], animal.dark);
      [-2, -1, 0, 1, 2].forEach((offset) => triangle(ctx, [[offset * 27 - 26, -111], [offset * 27, -155 + Math.abs(offset) * 7], [offset * 27 + 26, -111]], animal.accent));
      break;
    case "bat":
      triangle(ctx, [[-83, -73], [-113, -156], [-30, -109]], animal.dark);
      triangle(ctx, [[83, -73], [113, -156], [30, -109]], animal.dark);
      triangle(ctx, [[-101, 10], [-174, -42], [-151, 36], [-185, 75], [-107, 65]], animal.color);
      triangle(ctx, [[101, 10], [174, -42], [151, 36], [185, 75], [107, 65]], animal.color);
      break;
    case "seal":
      ellipse(ctx, -104, 31, 52, 29, animal.dark); ellipse(ctx, 104, 31, 52, 29, animal.dark);
      break;
    case "dolphin":
      triangle(ctx, [[0, -100], [-11, -170], [49, -108]], animal.dark);
      triangle(ctx, [[-96, 27], [-154, 64], [-102, 76]], animal.color);
      triangle(ctx, [[96, 27], [154, 64], [102, 76]], animal.color);
      break;
    case "whale":
      triangle(ctx, [[-95, 29], [-161, 63], [-102, 78]], animal.color);
      triangle(ctx, [[95, 29], [161, 63], [102, 78]], animal.color);
      ctx.strokeStyle = animal.accent; ctx.lineWidth = 7; ctx.beginPath();
      ctx.moveTo(0, -113); ctx.quadraticCurveTo(-22, -152, -52, -158);
      ctx.moveTo(0, -113); ctx.quadraticCurveTo(22, -152, 52, -158); ctx.stroke();
      break;
    case "crab":
      [-1, 1].forEach((side) => {
        ctx.strokeStyle = animal.dark; ctx.lineWidth = 12; ctx.beginPath(); ctx.moveTo(side * 83, -18); ctx.lineTo(side * 137, -66); ctx.stroke();
        ellipse(ctx, side * 151, -76, 39, 32, animal.color);
        triangle(ctx, [[side * 151, -76], [side * 185, -110], [side * 181, -64]], animal.dark);
        ctx.strokeStyle = animal.dark; ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(side * 48, -103); ctx.lineTo(side * 58, -153); ctx.stroke();
        ellipse(ctx, side * 59, -159, 22, 25, animal.color);
      });
      break;
    case "jellyfish":
      [-94, -57, -19, 19, 57, 94].forEach((x, index) => {
        ctx.strokeStyle = index % 2 ? animal.accent : animal.color; ctx.lineWidth = 22; ctx.beginPath();
        ctx.moveTo(x, 68); ctx.bezierCurveTo(x - 22, 103, x + 22, 120, x, 155); ctx.stroke();
      });
      break;
    case "turtle":
      strokeEllipse(ctx, 0, 5, 137, 148, animal.dark, 31);
      [-1, 1].forEach((side) => { ellipse(ctx, side * 127, 12, 42, 29, animal.color); });
      break;
    case "snake":
      [-1, 1].forEach((side) => triangle(ctx, [[side * 68, -91], [side * 141, -33], [side * 103, 60]], animal.accent));
      [-62, -31, 0, 31, 62].forEach((x, i) => triangle(ctx, [[x - 18, -112], [x, -146 - Math.abs(i - 2) * 4], [x + 18, -112]], animal.dark));
      break;
    case "armadillo":
      ellipse(ctx, -88, -103, 30, 42, animal.dark); ellipse(ctx, 88, -103, 30, 42, animal.dark);
      ellipse(ctx, -88, -103, 14, 23, animal.accent); ellipse(ctx, 88, -103, 14, 23, animal.accent);
      strokeEllipse(ctx, 0, 0, 128, 139, animal.dark, 15);
      break;
    case "walrus":
      ellipse(ctx, -114, 22, 51, 77, animal.dark); ellipse(ctx, 114, 22, 51, 77, animal.dark);
      ellipse(ctx, -95, -94, 26, 31, animal.color); ellipse(ctx, 95, -94, 26, 31, animal.color);
      break;
    case "orangutan":
      [-1, 1].forEach((side) => {
        ellipse(ctx, side * 112, -10, 67, 104, animal.dark);
        [-68, -28, 15, 57].forEach((y, index) => ellipse(ctx, side * (117 + index % 2 * 9), y, 43, 49, animal.color));
        ellipse(ctx, side * 123, -54, 31, 39, animal.accent);
      });
      break;
    case "baboon":
      ellipse(ctx, -112, -52, 48, 61, animal.dark); ellipse(ctx, 112, -52, 48, 61, animal.dark);
      ellipse(ctx, -112, -52, 27, 37, animal.accent); ellipse(ctx, 112, -52, 27, 37, animal.accent);
      [-45, -15, 15, 45].forEach((x, index) => ellipse(ctx, x, -127 - (index % 2) * 10, 27, 49, index % 2 ? animal.color : animal.dark));
      break;
    case "platypus":
      ellipse(ctx, -93, -95, 27, 34, animal.dark); ellipse(ctx, 93, -95, 27, 34, animal.dark);
      ctx.save(); ctx.translate(123, 53); ctx.rotate(-.46); ellipse(ctx, 0, 0, 45, 91, animal.dark); ctx.restore();
      break;
    case "anteater":
      ellipse(ctx, -92, -104, 31, 45, animal.dark); ellipse(ctx, 92, -104, 31, 45, animal.dark);
      [-48, -16, 16, 48].forEach((x, index) => triangle(ctx, [[x - 27, -111], [x, -160 - Math.abs(index - 1.5) * 7], [x + 27, -111]], index % 2 ? animal.dark : animal.accent));
      break;
    case "tapir":
      triangle(ctx, [[-84, -79], [-137, -129], [-106, -38]], animal.color);
      triangle(ctx, [[84, -79], [137, -129], [106, -38]], animal.color);
      triangle(ctx, [[-88, -88], [-125, -118], [-106, -61]], animal.accent);
      triangle(ctx, [[88, -88], [125, -118], [106, -61]], animal.accent);
      break;
    case "okapi":
      ellipse(ctx, -72, -137, 26, 67, animal.color); ellipse(ctx, 72, -137, 26, 67, animal.color);
      ellipse(ctx, -72, -139, 11, 47, animal.accent); ellipse(ctx, 72, -139, 11, 47, animal.accent);
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 11; ctx.beginPath();
      ctx.moveTo(-34, -111); ctx.lineTo(-37, -164); ctx.moveTo(34, -111); ctx.lineTo(37, -164); ctx.stroke();
      ellipse(ctx, -37, -169, 14, 14, animal.dark); ellipse(ctx, 37, -169, 14, 14, animal.dark);
      break;
    case "hyena":
      ellipse(ctx, -101, -98, 47, 58, animal.dark); ellipse(ctx, 101, -98, 47, 58, animal.dark);
      ellipse(ctx, -101, -98, 24, 32, animal.accent); ellipse(ctx, 101, -98, 24, 32, animal.accent);
      [-56, -28, 0, 28, 56].forEach((x, index) => triangle(ctx, [[x - 21, -111], [x, -162 - (index % 2) * 15], [x + 21, -111]], animal.dark));
      break;
    case "warthog":
      triangle(ctx, [[-86, -79], [-144, -111], [-108, -32]], animal.color);
      triangle(ctx, [[86, -79], [144, -111], [108, -32]], animal.color);
      triangle(ctx, [[-88, -87], [-130, -105], [-107, -54]], animal.accent);
      triangle(ctx, [[88, -87], [130, -105], [107, -54]], animal.accent);
      break;
    case "buffalo":
      ctx.strokeStyle = animal.accent; ctx.lineWidth = 30; ctx.beginPath();
      ctx.moveTo(-53, -104); ctx.bezierCurveTo(-93, -163, -158, -151, -151, -93); ctx.bezierCurveTo(-145, -61, -168, -64, -178, -87);
      ctx.moveTo(53, -104); ctx.bezierCurveTo(93, -163, 158, -151, 151, -93); ctx.bezierCurveTo(145, -61, 168, -64, 178, -87); ctx.stroke();
      ellipse(ctx, -111, -68, 38, 47, animal.dark); ellipse(ctx, 111, -68, 38, 47, animal.dark);
      break;
    case "camel":
      ellipse(ctx, -78, -144, 25, 72, animal.color); ellipse(ctx, 78, -144, 25, 72, animal.color);
      ellipse(ctx, -78, -146, 10, 49, animal.accent); ellipse(ctx, 78, -146, 10, 49, animal.accent);
      [-36, -12, 12, 36].forEach((x, index) => ellipse(ctx, x, -123 - (index % 2) * 10, 27, 33, animal.dark));
      break;
    case "porcupine":
      for (let i = 0; i < 18; i += 1) {
        const angle = (i / 18) * Math.PI * 2;
        const x = Math.cos(angle) * 115; const y = Math.sin(angle) * 129 - 5;
        const tipX = Math.cos(angle) * 184; const tipY = Math.sin(angle) * 201 - 5;
        const side = angle + Math.PI / 2;
        triangle(ctx, [[x + Math.cos(side) * 15, y + Math.sin(side) * 15], [tipX, tipY], [x - Math.cos(side) * 15, y - Math.sin(side) * 15]], i % 2 ? animal.accent : animal.dark);
      }
      break;
    case "skunk":
      triangle(ctx, [[-82, -76], [-126, -145], [-27, -107]], animal.dark);
      triangle(ctx, [[82, -76], [126, -145], [27, -107]], animal.dark);
      ctx.save(); ctx.translate(123, 17); ctx.rotate(-.3);
      ellipse(ctx, 0, 0, 47, 105, animal.dark); ellipse(ctx, -2, -11, 20, 83, animal.accent); ctx.restore();
      break;
    case "beaver":
      ellipse(ctx, -94, -95, 38, 43, animal.dark); ellipse(ctx, 94, -95, 38, 43, animal.dark);
      ellipse(ctx, -94, -95, 19, 23, animal.accent); ellipse(ctx, 94, -95, 19, 23, animal.accent);
      ctx.save(); ctx.translate(139, 34); ctx.rotate(.36); ellipse(ctx, 0, 0, 39, 82, animal.dark); ctx.restore();
      break;
    case "hedgehog":
      for (let i = 0; i < 16; i += 1) {
        const angle = (i / 16) * Math.PI * 2;
        const x = Math.cos(angle) * 106; const y = Math.sin(angle) * 121 - 5;
        const tipX = Math.cos(angle) * 165; const tipY = Math.sin(angle) * 177 - 5;
        const side = angle + Math.PI / 2;
        triangle(ctx, [[x + Math.cos(side) * 20, y + Math.sin(side) * 20], [tipX, tipY], [x - Math.cos(side) * 20, y - Math.sin(side) * 20]], animal.dark);
      }
      break;
    case "rooster":
      [-48, -17, 16, 49].forEach((x, index) => ellipse(ctx, x, -137 - (index === 1 || index === 2 ? 18 : 0), 29, 49, animal.accent));
      triangle(ctx, [[-95, 10], [-157, 49], [-105, 77]], animal.dark); triangle(ctx, [[95, 10], [157, 49], [105, 77]], animal.dark);
      break;
    case "turkey":
      for (let i = 0; i < 11; i += 1) {
        const angle = Math.PI + (i / 10) * Math.PI;
        const x = Math.cos(angle) * 120; const y = Math.sin(angle) * 119 - 9;
        ellipse(ctx, x, y, 38, 70, i % 2 ? animal.accent : animal.dark);
        ellipse(ctx, x, y - 10, 18, 43, i % 2 ? "#E9A94C" : animal.color);
      }
      break;
    case "puffin":
      triangle(ctx, [[-90, 3], [-153, 66], [-104, 78]], animal.dark); triangle(ctx, [[90, 3], [153, 66], [104, 78]], animal.dark);
      [-1, 0, 1].forEach((offset) => ellipse(ctx, offset * 24, -127 + Math.abs(offset) * 9, 18, 48, animal.dark));
      break;
    case "cockatoo":
      [-2, -1, 0, 1, 2].forEach((offset) => {
        ctx.save(); ctx.translate(offset * 24, -128 + Math.abs(offset) * 12); ctx.rotate(offset * .28);
        ellipse(ctx, 0, -24, 21, 71, offset % 2 ? animal.color : animal.accent); ctx.restore();
      });
      triangle(ctx, [[-93, 6], [-154, 62], [-104, 78]], animal.color); triangle(ctx, [[93, 6], [154, 62], [104, 78]], animal.color);
      break;
    case "ostrich":
      [-2, -1, 0, 1, 2].forEach((offset) => {
        ctx.save(); ctx.translate(offset * 35, -127 + Math.abs(offset) * 14); ctx.rotate(offset * .31);
        ellipse(ctx, 0, -19, 34, 65, offset % 2 ? animal.color : animal.accent); ctx.restore();
      });
      break;
    case "squid":
      triangle(ctx, [[-91, -75], [-159, -111], [-116, -9]], animal.accent);
      triangle(ctx, [[91, -75], [159, -111], [116, -9]], animal.accent);
      [-102, -61, -20, 20, 61, 102].forEach((x, index) => {
        ctx.strokeStyle = index % 2 ? animal.accent : animal.color; ctx.lineWidth = 25; ctx.beginPath();
        ctx.moveTo(x, 67); ctx.bezierCurveTo(x - 25, 111, x + 23, 130, x + (index - 2.5) * 8, 166); ctx.stroke();
      });
      break;
    case "lobster":
      [-1, 1].forEach((side) => {
        ctx.strokeStyle = animal.dark; ctx.lineWidth = 14; ctx.beginPath(); ctx.moveTo(side * 82, -18); ctx.lineTo(side * 137, -75); ctx.stroke();
        ellipse(ctx, side * 151, -84, 43, 37, animal.color);
        triangle(ctx, [[side * 149, -84], [side * 188, -121], [side * 181, -75]], animal.dark);
        ctx.strokeStyle = animal.dark; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(side * 43, -104); ctx.quadraticCurveTo(side * 86, -168, side * 133, -176); ctx.stroke();
      });
      break;
    case "seahorse":
      [-65, -33, 0, 33, 65].forEach((x, index) => triangle(ctx, [[x - 18, -111], [x, -153 - Math.abs(index - 2) * 6], [x + 18, -111]], animal.dark));
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 23; ctx.beginPath();
      ctx.moveTo(103, 53); ctx.bezierCurveTo(174, 60, 172, 137, 121, 137); ctx.bezierCurveTo(85, 137, 86, 99, 116, 101); ctx.stroke();
      break;
    case "stingray":
      triangle(ctx, [[0, -114], [-190, 37], [0, 102], [190, 37]], animal.color);
      triangle(ctx, [[-103, 2], [-193, 37], [-109, 71]], animal.accent); triangle(ctx, [[103, 2], [193, 37], [109, 71]], animal.accent);
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 13; ctx.beginPath(); ctx.moveTo(0, 92); ctx.bezierCurveTo(12, 132, -19, 164, 13, 198); ctx.stroke();
      break;
    case "pufferfish":
      for (let i = 0; i < 20; i += 1) {
        const angle = (i / 20) * Math.PI * 2;
        const x = Math.cos(angle) * 111; const y = Math.sin(angle) * 124 - 5;
        const tipX = Math.cos(angle) * 158; const tipY = Math.sin(angle) * 173 - 5;
        const side = angle + Math.PI / 2;
        triangle(ctx, [[x + Math.cos(side) * 13, y + Math.sin(side) * 13], [tipX, tipY], [x - Math.cos(side) * 13, y - Math.sin(side) * 13]], i % 2 ? animal.accent : animal.dark);
      }
      break;
    case "horse":
      triangle(ctx, [[-79,-78],[-134,-151],[-102,-35]], animal.color); triangle(ctx, [[79,-78],[134,-151],[102,-35]], animal.color);
      triangle(ctx, [[-82,-88],[-119,-134],[-103,-59]], animal.accent); triangle(ctx, [[82,-88],[119,-134],[103,-59]], animal.accent);
      [-46,-17,14,45].forEach((x, index) => ellipse(ctx, x, -134 - (index % 2) * 12, 25, 43, index % 2 ? animal.dark : animal.accent));
      break;
    case "donkey":
      ellipse(ctx, -78, -151, 27, 82, animal.color); ellipse(ctx, 78, -151, 27, 82, animal.color);
      ellipse(ctx, -78, -154, 11, 59, animal.accent); ellipse(ctx, 78, -154, 11, 59, animal.accent);
      [-30,0,30].forEach((x) => ellipse(ctx, x, -132, 22, 37, animal.dark));
      break;
    case "sheep":
      for (let i = 0; i < 16; i += 1) {
        const angle = (i / 16) * Math.PI * 2;
        ellipse(ctx, Math.cos(angle) * 112, Math.sin(angle) * 126 - 7, 42, 43, i % 2 ? animal.color : "#FFF9EA");
      }
      ellipse(ctx, -108, -50, 37, 53, animal.dark); ellipse(ctx, 108, -50, 37, 53, animal.dark);
      break;
    case "squirrel":
      triangle(ctx, [[-81,-79],[-130,-143],[-105,-40]], animal.color); triangle(ctx, [[81,-79],[130,-143],[105,-40]], animal.color);
      ellipse(ctx, 151, 12, 72, 111, animal.dark); ellipse(ctx, 148, 6, 47, 82, animal.accent);
      break;
    case "mouse":
      ellipse(ctx, -105, -91, 58, 62, animal.color); ellipse(ctx, 105, -91, 58, 62, animal.color);
      ellipse(ctx, -105, -91, 35, 39, animal.accent); ellipse(ctx, 105, -91, 35, 39, animal.accent);
      break;
    case "hamster":
      ellipse(ctx, -91, -105, 37, 42, animal.dark); ellipse(ctx, 91, -105, 37, 42, animal.dark);
      ellipse(ctx, -91, -105, 19, 22, animal.accent); ellipse(ctx, 91, -105, 19, 22, animal.accent);
      break;
    case "duck":
      [-55,-19,19,55].forEach((x, index) => ellipse(ctx, x, -130 - (index === 1 || index === 2 ? 13 : 0), 27, 43, index % 2 ? animal.accent : animal.color));
      triangle(ctx, [[-91,15],[-151,61],[-103,76]], animal.accent); triangle(ctx, [[91,15],[151,61],[103,76]], animal.accent);
      break;
    case "goose":
      triangle(ctx, [[-92,11],[-158,56],[-104,77]], animal.color); triangle(ctx, [[92,11],[158,56],[104,77]], animal.color);
      ellipse(ctx, 0, -137, 34, 54, animal.color); ellipse(ctx, 0, -169, 26, 23, animal.dark);
      break;
    case "swan":
      triangle(ctx, [[-91,6],[-168,44],[-105,81]], animal.color); triangle(ctx, [[91,6],[168,44],[105,81]], animal.color);
      ctx.strokeStyle = animal.color; ctx.lineWidth = 32; ctx.beginPath(); ctx.moveTo(-66,-85); ctx.bezierCurveTo(-128,-162,-24,-190,18,-140); ctx.stroke();
      break;
    case "crow":
      triangle(ctx, [[-93,-4],[-164,-75],[-108,73]], animal.dark); triangle(ctx, [[93,-4],[164,-75],[108,73]], animal.dark);
      [-43,-14,15,44].forEach((x) => triangle(ctx, [[x-20,-109],[x,-158],[x+20,-109]], animal.accent));
      break;
    case "bumblebee":
      for (let index = 0; index < 14; index += 1) {
        const angle = (index / 14) * Math.PI * 2;
        ellipse(ctx, Math.cos(angle) * 108, Math.sin(angle) * 114 - 1, 43, 41, index % 2 ? animal.dark : "#57432C");
      }
      [-1,1].forEach((side) => {
        ctx.save(); ctx.translate(side * 126, -36); ctx.rotate(side * .2);
        ellipse(ctx, 0, 0, 63, 72, "rgba(218,246,255,.82)");
        strokeEllipse(ctx, 0, 0, 63, 72, "rgba(61,51,43,.52)", 7);
        ctx.strokeStyle = "rgba(61,51,43,.35)"; ctx.lineWidth = 5; ctx.beginPath();
        ctx.moveTo(side * -34, 39); ctx.quadraticCurveTo(0, -6, side * 27, -53);
        ctx.moveTo(side * -22, 49); ctx.quadraticCurveTo(7, 14, side * 42, -20); ctx.stroke(); ctx.restore();
        ctx.save(); ctx.translate(side * 134, 46); ctx.rotate(side * .14);
        ellipse(ctx, 0, 0, 49, 56, "rgba(195,235,255,.7)");
        strokeEllipse(ctx, 0, 0, 49, 56, "rgba(61,51,43,.42)", 6); ctx.restore();
        ctx.strokeStyle = animal.dark; ctx.lineWidth = 9; ctx.beginPath();
        ctx.moveTo(side * 38, -101); ctx.quadraticCurveTo(side * 54, -148, side * 84, -151); ctx.stroke();
        ellipse(ctx, side * 88, -153, 20, 20, animal.accent); strokeEllipse(ctx, side * 88, -153, 20, 20, animal.dark, 6);
      });
      break;
    case "butterfly":
      [-1,1].forEach((side) => {
        ellipse(ctx, side * 132,-46,73,86,animal.color); ellipse(ctx,side * 144,63,58,68,animal.accent);
        ellipse(ctx,side * 137,-48,28,35,"#FFE36E"); ellipse(ctx,side * 148,62,20,25,"#68D6C2");
        ctx.strokeStyle = animal.dark; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(side * 31,-105); ctx.quadraticCurveTo(side * 67,-169,side * 104,-164); ctx.stroke();
      });
      break;
    case "ladybug":
      ellipse(ctx,-103,-11,69,116,animal.color); ellipse(ctx,103,-11,69,116,animal.color);
      [-1,1].forEach((side) => { ctx.strokeStyle = animal.dark; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(side * 39,-103); ctx.quadraticCurveTo(side * 72,-165,side * 101,-158); ctx.stroke(); ellipse(ctx,side * 104,-160,14,14,animal.dark); });
      break;
    case "mantis":
      [-1,1].forEach((side) => {
        ctx.strokeStyle = animal.dark; ctx.lineWidth = 12; ctx.beginPath(); ctx.moveTo(side * 74,20); ctx.lineTo(side * 143,-48); ctx.lineTo(side * 181,9); ctx.stroke();
        ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(side * 42,-106); ctx.quadraticCurveTo(side * 74,-175,side * 120,-178); ctx.stroke(); ellipse(ctx,side * 123,-180,13,13,animal.accent);
      });
      triangle(ctx,[[-89,-79],[-139,-134],[-106,-27]],animal.color); triangle(ctx,[[89,-79],[139,-134],[106,-27]],animal.color);
      break;
    case "snail":
      ellipse(ctx,137,25,91,101,animal.accent); strokeEllipse(ctx,137,25,55,62,animal.dark,10); strokeEllipse(ctx,137,25,24,29,animal.dark,8);
      [-1,1].forEach((side) => { ctx.strokeStyle = animal.dark; ctx.lineWidth = 10; ctx.beginPath(); ctx.moveTo(side * 46,-101); ctx.quadraticCurveTo(side * 70,-164,side * 103,-169); ctx.stroke(); ellipse(ctx,side * 106,-171,17,17,animal.dark); });
      break;
  }
}

function drawExtraDetails(ctx: CanvasRenderingContext2D, animal: Animal) {
  switch (animal.id) {
    case "panda":
      ellipse(ctx, -49, -28, 49, 43, animal.dark);
      ellipse(ctx, 49, -28, 49, 43, animal.dark);
      break;
    case "elephant":
      ctx.strokeStyle = "rgba(53, 69, 82, .38)";
      ctx.lineWidth = 5;
      ctx.beginPath();
      ctx.moveTo(-26, -92); ctx.quadraticCurveTo(0, -76, 26, -92);
      ctx.stroke();
      break;
    case "giraffe":
      [[-73, -83, 24, 30], [61, -86, 27, 22], [-92, 20, 23, 31], [81, 35, 28, 34], [0, -116, 24, 19]].forEach(([x, y, rx, ry]) => ellipse(ctx, x, y, rx, ry, animal.dark));
      break;
    case "monkey":
      ellipse(ctx, 0, -4, 90, 104, animal.accent);
      break;
    case "koala":
      ellipse(ctx, -77, 18, 30, 38, "rgba(247, 208, 215, .55)");
      ellipse(ctx, 77, 18, 30, 38, "rgba(247, 208, 215, .55)");
      break;
    case "zebra":
      [-67, 0, 67].forEach((x, index) => {
        triangle(ctx, [[x - 20, -126], [x, -73 + Math.abs(index - 1) * 8], [x + 20, -126]], animal.dark);
      });
      ctx.strokeStyle = animal.dark;
      ctx.lineWidth = 11;
      ctx.beginPath();
      ctx.moveTo(-112, -12); ctx.lineTo(-74, 3);
      ctx.moveTo(112, -12); ctx.lineTo(74, 3);
      ctx.stroke();
      break;
    case "fox":
      triangle(ctx, [[-118, 5], [-16, -45], [-55, 72]], animal.accent);
      triangle(ctx, [[118, 5], [16, -45], [55, 72]], animal.accent);
      break;
    case "bunny":
      ellipse(ctx, -75, 21, 23, 18, "rgba(255, 185, 210, .7)");
      ellipse(ctx, 75, 21, 23, 18, "rgba(255, 185, 210, .7)");
      break;
    case "pig":
      ellipse(ctx, -72, 10, 26, 20, "rgba(255, 209, 215, .62)");
      ellipse(ctx, 72, 10, 26, 20, "rgba(255, 209, 215, .62)");
      break;
    case "dog":
      ellipse(ctx, -50, -30, 51, 49, animal.dark);
      break;
    case "cat":
      [-49, 0, 49].forEach((x, index) => {
        triangle(ctx, [[x - 14, -123], [x, -83 + Math.abs(index - 1) * 5], [x + 14, -123]], animal.dark);
      });
      break;
    case "owl":
      ellipse(ctx, -54, -27, 58, 61, animal.accent);
      ellipse(ctx, 54, -27, 58, 61, animal.accent);
      strokeEllipse(ctx, -54, -27, 47, 50, animal.dark, 7);
      strokeEllipse(ctx, 54, -27, 47, 50, animal.dark, 7);
      break;
    case "penguin":
      ellipse(ctx, -49, -27, 58, 78, animal.accent);
      ellipse(ctx, 49, -27, 58, 78, animal.accent);
      ellipse(ctx, 0, 75, 78, 53, animal.accent);
      break;
    case "sloth":
      ctx.save(); ctx.rotate(-0.14); ellipse(ctx, -47, -23, 55, 35, animal.dark); ctx.restore();
      ctx.save(); ctx.rotate(0.14); ellipse(ctx, 47, -23, 55, 35, animal.dark); ctx.restore();
      break;
    case "deer":
      triangle(ctx, [[-28, -126], [0, 80], [28, -126]], animal.accent);
      ellipse(ctx, -84, -45, 9, 9, animal.accent);
      ellipse(ctx, 84, -45, 9, 9, animal.accent);
      break;
    case "flamingo":
      ellipse(ctx, 0, -22, 95, 102, animal.accent);
      break;
    case "parrot":
      ellipse(ctx, -55, 3, 47, 57, "#EAF8E4");
      ellipse(ctx, 55, 3, 47, 57, "#EAF8E4");
      ellipse(ctx, -97, 36, 27, 51, "#3F8FD2");
      break;
    case "shark":
      ctx.strokeStyle = animal.dark;
      ctx.lineWidth = 6;
      [-1, 0, 1].forEach((offset) => {
        ctx.beginPath(); ctx.moveTo(-103, 23 + offset * 14); ctx.lineTo(-78, 30 + offset * 14); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(103, 23 + offset * 14); ctx.lineTo(78, 30 + offset * 14); ctx.stroke();
      });
      break;
    case "octopus":
      [[-75, -72], [74, -78], [-96, 13], [92, 24], [-47, 83], [56, 90]].forEach(([x, y], index) => ellipse(ctx, x, y, 10 + (index % 2) * 4, 9 + (index % 3) * 3, animal.accent));
      break;
    case "chameleon":
      strokeEllipse(ctx, -65, -35, 43, 45, animal.accent, 10);
      strokeEllipse(ctx, 65, -35, 43, 45, animal.accent, 10);
      ellipse(ctx, -91, 41, 13, 13, animal.dark);
      ellipse(ctx, 91, 41, 13, 13, animal.dark);
      break;
    case "unicorn":
      triangle(ctx, [[0, -91], [-18, -58], [18, -58]], animal.accent);
      ellipse(ctx, -74, 23, 23, 16, "rgba(255, 185, 223, .7)");
      ellipse(ctx, 74, 23, 23, 16, "rgba(255, 185, 223, .7)");
      break;
    case "crocodile":
      [[-84, -75], [76, -83], [-104, 4], [98, 11]].forEach(([x, y], index) => ellipse(ctx, x, y, 14 + index * 2, 10 + (index % 2) * 4, animal.dark));
      break;
    case "kangaroo":
      triangle(ctx, [[-32, -119], [0, -67], [32, -119]], animal.accent);
      ellipse(ctx, -78, 18, 20, 14, "rgba(242,194,141,.65)"); ellipse(ctx, 78, 18, 20, 14, "rgba(242,194,141,.65)");
      break;
    case "rhino":
      strokeEllipse(ctx, 0, -11, 104, 111, "rgba(57,69,75,.28)", 8);
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(-37, -87); ctx.quadraticCurveTo(0, -72, 37, -87); ctx.stroke();
      break;
    case "gorilla":
      ellipse(ctx, 0, -5, 88, 101, animal.accent);
      ellipse(ctx, -79, -4, 22, 38, "rgba(255,255,255,.12)"); ellipse(ctx, 79, -4, 22, 38, "rgba(255,255,255,.12)");
      break;
    case "lemur":
      ctx.save(); ctx.rotate(-.12); ellipse(ctx, -48, -25, 57, 39, animal.dark); ctx.restore();
      ctx.save(); ctx.rotate(.12); ellipse(ctx, 48, -25, 57, 39, animal.dark); ctx.restore();
      triangle(ctx, [[-28, -119], [0, 66], [28, -119]], animal.accent);
      break;
    case "meerkat":
      [[-76, -63], [76, -63], [-95, 11], [95, 11]].forEach(([x, y]) => ellipse(ctx, x, y, 11, 8, animal.dark));
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(-104, 61); ctx.lineTo(-72, 55); ctx.moveTo(104, 61); ctx.lineTo(72, 55); ctx.stroke();
      break;
    case "redpanda":
      ellipse(ctx, -49, -30, 53, 45, animal.accent); ellipse(ctx, 49, -30, 53, 45, animal.accent);
      ellipse(ctx, -49, -30, 37, 29, animal.dark); ellipse(ctx, 49, -30, 37, 29, animal.dark);
      triangle(ctx, [[-27, -118], [0, 39], [27, -118]], animal.accent);
      break;
    case "leopard":
      [[-77,-75],[-3,-105],[75,-68],[-98,3],[93,14],[-69,75],[66,83]].forEach(([x,y], i) => {
        strokeEllipse(ctx, x, y, 12 + i % 3, 10 + i % 2, animal.dark, 7);
      });
      break;
    case "cheetah":
      [[-77,-78],[-19,-110],[71,-73],[-99,9],[94,15],[-77,74],[76,80]].forEach(([x,y], i) => ellipse(ctx, x, y, 7 + i % 3, 7 + i % 2, animal.dark));
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(-45,-16); ctx.quadraticCurveTo(-48,23,-37,49); ctx.moveTo(45,-16); ctx.quadraticCurveTo(48,23,37,49); ctx.stroke();
      break;
    case "wolf":
      triangle(ctx, [[-118, 12], [0, -53], [-58, 78]], animal.accent); triangle(ctx, [[118, 12], [0, -53], [58, 78]], animal.accent);
      triangle(ctx, [[-25, -122], [0, 8], [25, -122]], "rgba(255,255,255,.25)");
      break;
    case "moose":
      ellipse(ctx, -81, 12, 22, 16, "rgba(201,151,109,.55)"); ellipse(ctx, 81, 12, 22, 16, "rgba(201,151,109,.55)");
      triangle(ctx, [[-24, -119], [0, 25], [24, -119]], animal.accent);
      break;
    case "ram":
      [-78,-39,0,39,78].forEach((x) => ellipse(ctx, x, -117, 33, 31, animal.accent));
      ellipse(ctx, -78, 17, 18, 13, "rgba(240,222,197,.5)"); ellipse(ctx, 78, 17, 18, 13, "rgba(240,222,197,.5)");
      break;
    case "alpaca":
      [-90,-45,0,45,90].forEach((x, i) => ellipse(ctx, x, -103 + Math.abs(i - 2) * 7, 38, 36, animal.accent));
      ellipse(ctx, -76, 19, 21, 15, "rgba(255,255,255,.45)"); ellipse(ctx, 76, 19, 21, 15, "rgba(255,255,255,.45)");
      break;
    case "toucan":
      ellipse(ctx, -46, -18, 57, 67, "#FFF8E2"); ellipse(ctx, 46, -18, 57, 67, "#FFF8E2");
      ellipse(ctx, -93, 54, 25, 48, animal.accent);
      break;
    case "peacock":
      ellipse(ctx, -49, -23, 55, 68, animal.accent); ellipse(ctx, 49, -23, 55, 68, animal.accent);
      [-58, 0, 58].forEach((x) => { ctx.strokeStyle = animal.dark; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(x, -111); ctx.lineTo(x, -154); ctx.stroke(); ellipse(ctx, x, -160, 12, 18, animal.accent); });
      break;
    case "pelican":
      ellipse(ctx, -49, -28, 56, 73, "#FFFDF5"); ellipse(ctx, 49, -28, 56, 73, "#FFFDF5");
      break;
    case "eagle":
      ellipse(ctx, 0, -27, 108, 101, animal.accent);
      [-90,-54,-18,18,54,90].forEach((x) => triangle(ctx, [[x-18,36],[x,75],[x+18,36]], animal.accent));
      break;
    case "bat":
      triangle(ctx, [[-112, 22], [0, -48], [-54, 85]], animal.accent); triangle(ctx, [[112, 22], [0, -48], [54, 85]], animal.accent);
      break;
    case "seal":
      [[-87,-71],[80,-80],[-101,3],[94,14]].forEach(([x,y], i) => ellipse(ctx, x, y, 11 + i * 2, 8 + i % 2 * 4, "rgba(49,74,82,.35)"));
      break;
    case "dolphin":
      ellipse(ctx, -80, 23, 17, 12, animal.accent); ellipse(ctx, 80, 23, 17, 12, animal.accent);
      ctx.strokeStyle = "rgba(205,239,252,.55)"; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(-63,-91); ctx.quadraticCurveTo(0,-69,63,-91); ctx.stroke();
      break;
    case "whale":
      [[-82,-61],[-13,-99],[72,-70],[-99,3],[96,17]].forEach(([x,y], i) => ellipse(ctx, x, y, 8 + i % 3, 7 + i % 2, animal.accent));
      break;
    case "crab":
      ellipse(ctx, -56, -26, 39, 42, animal.accent); ellipse(ctx, 56, -26, 39, 42, animal.accent);
      [[-92,49],[-53,79],[53,79],[92,49]].forEach(([x,y]) => { ctx.strokeStyle = animal.dark; ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(x * .75, y); ctx.lineTo(x, y + 28); ctx.stroke(); });
      break;
    case "jellyfish":
      [[-75,-61],[-12,-103],[69,-63],[-92,17],[89,20]].forEach(([x,y], i) => ellipse(ctx, x, y, 12 + i % 2 * 5, 10 + i % 3, animal.accent));
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(-111,54); ctx.quadraticCurveTo(-86,79,-61,54); ctx.quadraticCurveTo(-34,79,-7,54); ctx.quadraticCurveTo(20,79,47,54); ctx.quadraticCurveTo(74,79,105,54); ctx.stroke();
      break;
    case "turtle":
      [[0,-92],[-68,-54],[68,-54],[-78,29],[78,29],[0,72]].forEach(([x,y]) => strokeEllipse(ctx, x, y, 30, 29, animal.dark, 6));
      break;
    case "snake":
      [[-79,-65],[-18,-104],[64,-73],[-98,6],[91,20]].forEach(([x,y], i) => ellipse(ctx, x, y, 13 + i % 2 * 4, 9 + i % 3, animal.accent));
      break;
    case "armadillo":
      [-84,-56,-28,0,28,56,84].forEach((x) => { ctx.strokeStyle = animal.dark; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(x,-105); ctx.quadraticCurveTo(x * 1.2,0,x,105); ctx.stroke(); });
      break;
    case "walrus":
      [[-81,-66],[-15,-103],[74,-70],[-96,-3],[92,5]].forEach(([x,y], index) => ellipse(ctx, x, y, 9 + index % 2 * 3, 8 + index % 3, "rgba(70,49,57,.38)"));
      break;
    case "orangutan":
      ellipse(ctx, 0, -4, 91, 108, animal.accent);
      ellipse(ctx, -72, 24, 27, 35, "rgba(198,95,50,.5)"); ellipse(ctx, 72, 24, 27, 35, "rgba(198,95,50,.5)");
      break;
    case "baboon":
      ellipse(ctx, -51, -22, 53, 70, animal.accent); ellipse(ctx, 51, -22, 53, 70, animal.accent);
      triangle(ctx, [[-28, -119], [0, 45], [28, -119]], "#D04F6A");
      break;
    case "platypus":
      ctx.strokeStyle = "rgba(233,165,78,.55)"; ctx.lineWidth = 6; ctx.beginPath();
      ctx.moveTo(-74,-92); ctx.quadraticCurveTo(0,-71,74,-92); ctx.moveTo(-91,4); ctx.quadraticCurveTo(0,20,91,4); ctx.stroke();
      break;
    case "anteater":
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 25; ctx.beginPath(); ctx.moveTo(-88,-100); ctx.bezierCurveTo(-40,-49,8,-11,84,13); ctx.stroke();
      ctx.strokeStyle = animal.accent; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(-78,-100); ctx.bezierCurveTo(-31,-52,15,-21,76,1); ctx.stroke();
      break;
    case "tapir":
      ellipse(ctx, -75, 0, 42, 67, animal.accent); ellipse(ctx, 75, 0, 42, 67, animal.accent);
      triangle(ctx, [[-29,-123],[0,12],[29,-123]], "rgba(255,255,255,.17)");
      break;
    case "okapi":
      [-82,-54,-27,0,27,54,82].forEach((x, index) => {
        ctx.strokeStyle = animal.accent; ctx.lineWidth = 11; ctx.beginPath();
        ctx.moveTo(x, 42); ctx.lineTo(x * .82, 103 - Math.abs(index - 3) * 6); ctx.stroke();
      });
      ctx.strokeStyle = animal.accent; ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(-96,-68); ctx.lineTo(-66,-51); ctx.moveTo(96,-68); ctx.lineTo(66,-51); ctx.stroke();
      break;
    case "hyena":
      [[-75,-69],[-6,-102],[68,-74],[-96,2],[91,13],[-71,76],[70,82]].forEach(([x,y], index) => ellipse(ctx, x, y, 10 + index % 3 * 3, 8 + index % 2 * 3, animal.dark));
      break;
    case "warthog":
      ellipse(ctx, -86, 25, 24, 23, animal.accent); ellipse(ctx, 86, 25, 24, 23, animal.accent);
      ellipse(ctx, -89, 25, 10, 9, animal.dark); ellipse(ctx, 89, 25, 10, 9, animal.dark);
      break;
    case "buffalo":
      [-84,-50,-17,17,50,84].forEach((x, index) => ellipse(ctx, x, -103 + Math.abs(index - 2.5) * 5, 34, 31, index % 2 ? animal.dark : animal.color));
      ellipse(ctx, -80, 20, 21, 16, "rgba(205,174,124,.28)"); ellipse(ctx, 80, 20, 21, 16, "rgba(205,174,124,.28)");
      break;
    case "camel":
      ellipse(ctx, -74, 24, 24, 16, "rgba(242,208,149,.55)"); ellipse(ctx, 74, 24, 24, 16, "rgba(242,208,149,.55)");
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(-93,-5); ctx.quadraticCurveTo(-70,12,-51,-1); ctx.moveTo(93,-5); ctx.quadraticCurveTo(70,12,51,-1); ctx.stroke();
      break;
    case "porcupine":
      [-92,-63,-32,0,32,63,92].forEach((x, index) => {
        ctx.strokeStyle = index % 2 ? animal.accent : animal.dark; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(x,-102); ctx.lineTo(x * 1.12,-72); ctx.stroke();
      });
      break;
    case "skunk":
      ctx.strokeStyle = animal.accent; ctx.lineWidth = 31; ctx.beginPath(); ctx.moveTo(-42,-119); ctx.bezierCurveTo(-10,-79,-18,-23,0,17); ctx.bezierCurveTo(16,-23,11,-79,43,-119); ctx.stroke();
      ellipse(ctx, -75, 22, 21, 15, "rgba(255,248,229,.35)"); ellipse(ctx, 75, 22, 21, 15, "rgba(255,248,229,.35)");
      break;
    case "beaver":
      ellipse(ctx, -75, 16, 22, 16, "rgba(228,179,124,.52)"); ellipse(ctx, 75, 16, 22, 16, "rgba(228,179,124,.52)");
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(-104,-15); ctx.quadraticCurveTo(-78,-3,-58,-13); ctx.moveTo(104,-15); ctx.quadraticCurveTo(78,-3,58,-13); ctx.stroke();
      break;
    case "hedgehog":
      ellipse(ctx, 0, 0, 101, 113, animal.accent);
      triangle(ctx, [[-38,-113],[0,-72],[38,-113]], animal.color);
      break;
    case "rooster":
      ellipse(ctx, -49, -24, 55, 67, "#FFF8E7"); ellipse(ctx, 49, -24, 55, 67, "#FFF8E7");
      ellipse(ctx, -83, 40, 22, 37, animal.accent); ellipse(ctx, 83, 40, 22, 37, animal.accent);
      break;
    case "turkey":
      ellipse(ctx, -49, -26, 54, 67, animal.accent); ellipse(ctx, 49, -26, 54, 67, animal.accent);
      [-75,-38,0,38,75].forEach((x) => ellipse(ctx, x, 72, 13, 19, "#E8A949"));
      break;
    case "puffin":
      ellipse(ctx, -51, -28, 58, 75, animal.accent); ellipse(ctx, 51, -28, 58, 75, animal.accent);
      triangle(ctx, [[-110,-69],[-45,-38],[-85,-6]], "#E35245"); triangle(ctx, [[110,-69],[45,-38],[85,-6]], "#E35245");
      break;
    case "cockatoo":
      ellipse(ctx, -50, -25, 57, 71, "#FFF9E7"); ellipse(ctx, 50, -25, 57, 71, "#FFF9E7");
      ellipse(ctx, -76, 24, 22, 15, "rgba(255,134,151,.46)"); ellipse(ctx, 76, 24, 22, 15, "rgba(255,134,151,.46)");
      break;
    case "ostrich":
      ellipse(ctx, -50, -25, 57, 70, animal.accent); ellipse(ctx, 50, -25, 57, 70, animal.accent);
      [-1, 1].forEach((side) => {
        ctx.strokeStyle = animal.dark; ctx.lineWidth = 4; ctx.beginPath();
        [-2,-1,0,1,2].forEach((lash) => { ctx.moveTo(side * (55 + lash * 7), -59); ctx.lineTo(side * (58 + lash * 9), -79 - Math.abs(lash) * 2); }); ctx.stroke();
      });
      break;
    case "squid":
      [[-76,-70],[-10,-103],[69,-72],[-93,8],[89,13],[-58,78],[61,82]].forEach(([x,y], index) => ellipse(ctx, x, y, 9 + index % 3 * 3, 8 + index % 2 * 4, animal.accent));
      break;
    case "lobster":
      [-87,-58,-29,0,29,58,87].forEach((x) => { ctx.strokeStyle = animal.dark; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(x,-105); ctx.quadraticCurveTo(x * 1.08,0,x,105); ctx.stroke(); });
      ellipse(ctx, -58, -65, 18, 14, animal.accent); ellipse(ctx, 58, -65, 18, 14, animal.accent);
      break;
    case "seahorse":
      [[-78,-67],[-12,-104],[67,-73],[-94,4],[86,15],[-61,75],[58,81]].forEach(([x,y], index) => strokeEllipse(ctx, x, y, 12 + index % 2 * 4, 9 + index % 3, animal.dark, 5));
      break;
    case "stingray":
      ellipse(ctx, 0, -4, 101, 111, animal.accent);
      ellipse(ctx, -76, 28, 19, 13, "rgba(111,143,168,.48)"); ellipse(ctx, 76, 28, 19, 13, "rgba(111,143,168,.48)");
      break;
    case "pufferfish":
      [[-73,-73],[-10,-102],[65,-69],[-91,2],[88,10],[-65,72],[61,79]].forEach(([x,y], index) => ellipse(ctx, x, y, 10 + index % 2 * 4, 9 + index % 3, animal.dark));
      ellipse(ctx, -75, 28, 21, 15, "rgba(255,243,162,.65)"); ellipse(ctx, 75, 28, 21, 15, "rgba(255,243,162,.65)");
      break;
    case "horse":
      triangle(ctx, [[-23,-119],[0,-43],[23,-119]], animal.accent);
      ellipse(ctx,-78,25,21,15,"rgba(243,201,139,.52)"); ellipse(ctx,78,25,21,15,"rgba(243,201,139,.52)");
      break;
    case "donkey":
      ellipse(ctx,0,39,66,64,animal.accent);
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(-92,-2); ctx.quadraticCurveTo(-68,11,-49,-2); ctx.moveTo(92,-2); ctx.quadraticCurveTo(68,11,49,-2); ctx.stroke();
      break;
    case "sheep":
      [-69,-35,0,35,69].forEach((x,index) => ellipse(ctx,x,-113 - (index % 2) * 9,35,34,"#FFF9EA"));
      ellipse(ctx,-72,23,22,16,"rgba(233,183,194,.5)"); ellipse(ctx,72,23,22,16,"rgba(233,183,194,.5)");
      break;
    case "squirrel":
      ellipse(ctx,-76,30,30,27,animal.accent); ellipse(ctx,76,30,30,27,animal.accent);
      triangle(ctx,[[-20,-116],[0,-68],[20,-116]],animal.accent);
      break;
    case "mouse":
      ellipse(ctx,-75,27,25,21,"rgba(245,184,200,.65)"); ellipse(ctx,75,27,25,21,"rgba(245,184,200,.65)");
      break;
    case "hamster":
      ellipse(ctx,-78,25,40,47,animal.accent); ellipse(ctx,78,25,40,47,animal.accent);
      ellipse(ctx,-62,-68,35,31,"rgba(255,240,207,.65)");
      break;
    case "duck":
      ellipse(ctx,-48,-27,56,67,"rgba(255,247,205,.7)"); ellipse(ctx,48,-27,56,67,"rgba(255,247,205,.7)");
      break;
    case "goose":
      ellipse(ctx,-49,-26,57,72,"#FFFDF5"); ellipse(ctx,49,-26,57,72,"#FFFDF5");
      triangle(ctx,[[-18,-113],[0,-83],[18,-113]],animal.accent);
      break;
    case "swan":
      ellipse(ctx,-50,-27,58,73,"#FFFDF8"); ellipse(ctx,50,-27,58,73,"#FFFDF8");
      ctx.strokeStyle = animal.accent; ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(-83,43); ctx.quadraticCurveTo(0,84,83,43); ctx.stroke();
      break;
    case "crow":
      ellipse(ctx,-51,-29,58,73,animal.accent); ellipse(ctx,51,-29,58,73,animal.accent);
      triangle(ctx,[[-22,-117],[0,-74],[22,-117]],animal.dark);
      break;
    case "bumblebee":
      ctx.save();
      ctx.beginPath(); ctx.ellipse(0, -1, 128, 123, 0, 0, Math.PI * 2); ctx.clip();
      ctx.strokeStyle = animal.dark;
      [-91, 86].forEach((y, index) => {
        ctx.lineWidth = index ? 18 : 16;
        ctx.beginPath(); ctx.moveTo(-138, y + 5);
        ctx.quadraticCurveTo(0, y - 9 - index * 2, 138, y + 5); ctx.stroke();
      });
      ctx.restore();
      [-66,-33,0,33,66].forEach((x, index) => ellipse(ctx, x, -107 - (index % 2) * 6, 36, 32, index % 2 ? animal.color : animal.accent));
      [-1,1].forEach((side) => {
        ctx.strokeStyle = animal.dark; ctx.lineWidth = 13; ctx.beginPath();
        ctx.moveTo(side * 89, -1); ctx.quadraticCurveTo(side * 106, 5, side * 119, 13); ctx.stroke();
      });
      ellipse(ctx, -83, 35, 31, 24, "rgba(247,126,108,.62)"); ellipse(ctx, 83, 35, 31, 24, "rgba(247,126,108,.62)");
      [[-105,-51],[104,-51],[-108,59],[108,58]].forEach(([x,y]) => ellipse(ctx,x,y,8,8,"rgba(255,247,194,.78)"));
      break;
    case "butterfly":
      ellipse(ctx,0,-43,30,75,animal.dark); ellipse(ctx,0,61,39,67,animal.dark);
      ellipse(ctx,-74,22,22,18,"rgba(255,227,110,.7)"); ellipse(ctx,74,22,22,18,"rgba(255,227,110,.7)");
      break;
    case "ladybug":
      [[-73,-70],[0,-91],[72,-68],[-87,8],[86,9],[-61,73],[61,73]].forEach(([x,y]) => ellipse(ctx,x,y,17,19,animal.dark));
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 10; ctx.beginPath(); ctx.moveTo(0,-112); ctx.lineTo(0,109); ctx.stroke();
      break;
    case "mantis":
      triangle(ctx,[[-105,-74],[-31,-34],[-93,36]],animal.accent); triangle(ctx,[[105,-74],[31,-34],[93,36]],animal.accent);
      ellipse(ctx,0,3,34,105,animal.dark); ellipse(ctx,0,-8,15,82,animal.accent);
      break;
    case "snail":
      [[-74,-69],[-9,-98],[67,-70],[-88,3],[83,15],[-57,72],[57,76]].forEach(([x,y],index) => ellipse(ctx,x,y,11 + index % 2 * 4,9 + index % 3,animal.accent));
      ellipse(ctx,-73,27,21,15,"rgba(242,166,111,.45)"); ellipse(ctx,73,27,21,15,"rgba(242,166,111,.45)");
      break;
  }
}

function drawExtraMouth(ctx: CanvasRenderingContext2D, animal: Animal, pose: Pose, surprised: number) {
  const open = clamp((pose.mouth - 0.08) * 1.55);
  const muzzleIds = [
    "panda", "lion", "giraffe", "zebra", "fox", "bunny", "dog", "cat", "sloth", "bear", "deer", "unicorn",
    "kangaroo", "gorilla", "lemur", "meerkat", "redpanda", "leopard", "cheetah", "wolf", "moose", "ram", "alpaca", "bat", "seal", "armadillo",
    "okapi", "hyena", "porcupine", "skunk", "hedgehog", "horse", "donkey", "sheep", "squirrel", "mouse", "hamster",
  ];
  if (muzzleIds.includes(animal.id)) {
    const wide = ["lion", "bear", "panda", "gorilla", "moose", "seal", "hyena", "porcupine", "hedgehog", "horse", "donkey", "sheep", "hamster"].includes(animal.id);
    ellipse(ctx, 0, 39, wide ? 58 : 49, wide ? 46 : 40, animal.accent);
    const tinyNose = ["bunny", "meerkat", "bat", "hedgehog", "squirrel", "mouse", "hamster"].includes(animal.id);
    ellipse(ctx, 0, 24, tinyNose ? 13 : 18, tinyNose ? 10 : 13, animal.dark);
    drawMouth(ctx, animal, pose, 68);
    if (["fox", "bunny", "cat", "lemur", "redpanda", "leopard", "cheetah", "wolf", "seal", "porcupine", "skunk", "hedgehog", "squirrel", "mouse", "hamster"].includes(animal.id)) {
      ctx.strokeStyle = animal.dark;
      ctx.lineWidth = 3;
      [-1, 1].forEach((side) => {
        [-1, 0, 1].forEach((row) => {
          ctx.beginPath();
          ctx.moveTo(side * 31, 45 + row * 7);
          ctx.lineTo(side * 112, 36 + row * 15);
          ctx.stroke();
        });
      });
    }
    return true;
  }
  if (animal.id === "elephant") {
    ellipse(ctx, 0, 21, 22, 16, animal.dark);
    ctx.strokeStyle = animal.color;
    ctx.lineWidth = 38;
    ctx.beginPath();
    ctx.moveTo(0, 30);
    ctx.bezierCurveTo(-2, 60, -2 + open * 18, 99, 26 + open * 25, 104 - open * 8);
    ctx.stroke();
    ctx.strokeStyle = animal.accent;
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.moveTo(-7, 35); ctx.bezierCurveTo(-7, 62, -7 + open * 12, 88, 18 + open * 23, 96 - open * 7); ctx.stroke();
    ellipse(ctx, 25 + open * 25, 103 - open * 8, 7 + open * 5, 6 + open * 5, animal.dark);
    return true;
  }
  if (animal.id === "monkey") {
    ellipse(ctx, 0, 37, 65, 57, animal.accent);
    ellipse(ctx, 0, 19, 24, 14, animal.dark);
    drawMouth(ctx, animal, pose, 69);
    return true;
  }
  if (animal.id === "koala") {
    ellipse(ctx, 0, 25, 27, 35, animal.dark);
    drawMouth(ctx, animal, pose, 72);
    return true;
  }
  if (animal.id === "hippo") {
    ellipse(ctx, 0, 47, 86, 58, animal.accent);
    ellipse(ctx, -35, 34, 9, 11, animal.dark);
    ellipse(ctx, 35, 34, 9, 11, animal.dark);
    drawMouth(ctx, animal, pose, 79);
    return true;
  }
  if (animal.id === "pig") {
    ellipse(ctx, 0, 40, 63, 44, animal.accent);
    ellipse(ctx, -25, 38, 8, 12, animal.dark);
    ellipse(ctx, 25, 38, 8, 12, animal.dark);
    drawMouth(ctx, animal, pose, 78);
    return true;
  }
  if (["owl", "penguin", "parrot"].includes(animal.id)) {
    const beak = animal.id === "parrot" ? "#FF9E43" : animal.id === "penguin" ? "#FFB23E" : animal.accent;
    triangle(ctx, [[-36, 27], [0, -2], [36, 27]], beak);
    triangle(ctx, [[-34, 29], [0, 55 + surprised * 18], [34, 29]], animal.id === "owl" ? "#E5A642" : "#F17842");
    return true;
  }
  if (["duck", "goose", "swan", "crow"].includes(animal.id)) {
    const halfWidth = animal.id === "goose" ? 58 : animal.id === "swan" ? 52 : animal.id === "duck" ? 64 : 47;
    const beak = animal.id === "crow" ? animal.dark : animal.id === "swan" ? "#F08066" : animal.accent;
    triangle(ctx, [[-halfWidth,24],[0,-4],[halfWidth,24]], beak);
    triangle(ctx, [[-halfWidth + 5,29],[0,59 + surprised * 20],[halfWidth - 5,29]], animal.id === "crow" ? animal.accent : "#E77F39");
    if (animal.id === "swan") ellipse(ctx, 0, 8, 12, 9, animal.dark);
    return true;
  }
  if (animal.id === "flamingo") {
    ellipse(ctx, -3, 34, 43, 27, "#FFD46E");
    ellipse(ctx, 28, 39 + open * 8, 24 + open * 5, 24 + open * 8, animal.dark);
    if (open > .28) ellipse(ctx, 8, 47 + open * 14, 19, 7 + open * 7, "#F27A78");
    return true;
  }
  if (animal.id === "shark") {
    ellipse(ctx, 0, 45 + open * 7, 72, 27 + open * 26, animal.dark);
    [-48, -24, 0, 24, 48].forEach((x) => {
      triangle(ctx, [[x - 9, 25], [x, 43], [x + 9, 25]], "#FFFDF4");
      if (open > 0.25) triangle(ctx, [[x - 9, 67 + open * 15], [x, 50 + open * 8], [x + 9, 67 + open * 15]], "#FFFDF4");
    });
    return true;
  }
  if (animal.id === "octopus") {
    ellipse(ctx, 0, 47, 20 + open * 12, 14 + open * 27, animal.dark);
    if (open > 0.35) ellipse(ctx, 0, 56 + open * 9, 10, 7, animal.accent);
    return true;
  }
  if (animal.id === "chameleon") {
    ctx.strokeStyle = animal.dark;
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.moveTo(-32, 56); ctx.quadraticCurveTo(0, 70 + pose.smile * 12, 32, 54); ctx.stroke();
    if (open > 0.25) {
      ctx.strokeStyle = "#FF7CA8";
      ctx.lineWidth = 10;
      ctx.beginPath(); ctx.moveTo(18, 61); ctx.quadraticCurveTo(58, 69, 88, 47); ctx.stroke();
      ellipse(ctx, 91, 45, 12, 10, "#FF7CA8");
    }
    return true;
  }
  if (animal.id === "crocodile") {
    ellipse(ctx, 0, 50, 102, 46, animal.accent);
    ellipse(ctx, -48, 35, 8, 9, animal.dark);
    ellipse(ctx, 48, 35, 8, 9, animal.dark);
    ctx.strokeStyle = animal.dark;
    ctx.lineWidth = 7;
    ctx.beginPath(); ctx.moveTo(-86, 59); ctx.quadraticCurveTo(0, 70 + open * 20, 86, 59); ctx.stroke();
    [-58, -29, 0, 29, 58].forEach((x) => triangle(ctx, [[x - 7, 58], [x, 73 + open * 10], [x + 7, 58]], "#FFFDF4"));
    return true;
  }
  if (animal.id === "rhino") {
    ellipse(ctx, 0, 47, 78, 53, animal.accent);
    ellipse(ctx, -30, 34, 9, 11, animal.dark); ellipse(ctx, 30, 34, 9, 11, animal.dark);
    drawMouth(ctx, animal, pose, 79);
    return true;
  }
  if (["toucan", "peacock", "pelican", "eagle"].includes(animal.id)) {
    if (animal.id === "toucan") {
      ctx.save(); ctx.rotate(-.06); ellipse(ctx, 28, 30, 85, 31, animal.accent); ctx.restore();
      triangle(ctx, [[74, 22], [123, 33], [73, 47]], "#FF8D42");
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(-35, 34); ctx.quadraticCurveTo(30, 46 + open * 17, 102, 34); ctx.stroke();
    } else if (animal.id === "pelican") {
      triangle(ctx, [[-42, 18], [0, -2], [77, 25]], animal.accent);
      ctx.save(); ctx.rotate(-.08); ellipse(ctx, 24, 52, 78, 35 + open * 13, "#FF9C61"); ctx.restore();
    } else {
      const beak = animal.id === "peacock" ? "#FFD75B" : "#E7A63D";
      triangle(ctx, [[-39, 23], [0, -6], [39, 23]], beak);
      triangle(ctx, [[-35, 27], [0, 58 + surprised * 16], [35, 27]], animal.id === "eagle" ? "#C77B2C" : "#47B9A8");
    }
    return true;
  }
  if (["dolphin", "whale"].includes(animal.id)) {
    const isWhale = animal.id === "whale";
    ellipse(ctx, 0, 44, isWhale ? 87 : 73, isWhale ? 48 : 36, animal.accent);
    ellipse(ctx, -39, 31, 8, 8, animal.dark); ellipse(ctx, 39, 31, 8, 8, animal.dark);
    ctx.strokeStyle = animal.dark; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(-61, 58); ctx.quadraticCurveTo(0, 78 + pose.smile * 12 + open * 10, 61, 58); ctx.stroke();
    return true;
  }
  if (animal.id === "crab") {
    ellipse(ctx, 0, 48, 25 + open * 8, 13 + open * 25, animal.dark);
    if (open > .3) ellipse(ctx, 0, 59, 12, 6, "#FF7994");
    return true;
  }
  if (animal.id === "jellyfish") {
    ellipse(ctx, 0, 44, 17 + open * 12, 14 + open * 25, animal.dark);
    ellipse(ctx, -73, 24, 18, 12, "rgba(240,193,245,.55)"); ellipse(ctx, 73, 24, 18, 12, "rgba(240,193,245,.55)");
    return true;
  }
  if (animal.id === "turtle") {
    triangle(ctx, [[-35, 25], [0, 5], [35, 25]], animal.accent);
    triangle(ctx, [[-32, 29], [0, 56 + surprised * 16], [32, 29]], animal.dark);
    return true;
  }
  if (animal.id === "snake") {
    ctx.strokeStyle = animal.dark; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(-35, 45); ctx.quadraticCurveTo(0, 62 + pose.smile * 12, 35, 45); ctx.stroke();
    if (open > .16) {
      ctx.strokeStyle = "#F36B8C"; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(0, 54); ctx.lineTo(0, 95); ctx.moveTo(0, 94); ctx.lineTo(-13, 107); ctx.moveTo(0, 94); ctx.lineTo(13, 107); ctx.stroke();
    }
    return true;
  }
  if (animal.id === "walrus") {
    ellipse(ctx, -39, 43, 51, 50, animal.accent); ellipse(ctx, 39, 43, 51, 50, animal.accent);
    ellipse(ctx, 0, 22, 22, 15, animal.dark);
    triangle(ctx, [[-39,55],[-27,125],[-10,56]], "#FFF3D0"); triangle(ctx, [[39,55],[27,125],[10,56]], "#FFF3D0");
    ctx.strokeStyle = animal.dark; ctx.lineWidth = 3; [-1,1].forEach((side) => [-1,0,1].forEach((row) => {
      ctx.beginPath(); ctx.moveTo(side * 35, 44 + row * 9); ctx.lineTo(side * 121, 34 + row * 17); ctx.stroke();
    }));
    drawMouth(ctx, animal, pose, 83);
    return true;
  }
  if (animal.id === "orangutan") {
    ellipse(ctx, 0, 38, 67, 58, animal.accent); ellipse(ctx, 0, 17, 25, 15, animal.dark);
    drawMouth(ctx, animal, pose, 72);
    return true;
  }
  if (animal.id === "baboon") {
    ellipse(ctx, 0, 43, 48, 74, "#D98496"); ellipse(ctx, -17, 14, 8, 12, animal.dark); ellipse(ctx, 17, 14, 8, 12, animal.dark);
    drawMouth(ctx, animal, pose, 70);
    return true;
  }
  if (animal.id === "platypus") {
    ctx.save(); ctx.translate(0, 42 + open * 6);
    ellipse(ctx, 0, -8, 86, 31 + open * 7, animal.accent);
    ellipse(ctx, 0, 15 + open * 12, 79, 23 + open * 8, "#C8793B");
    ctx.strokeStyle = animal.dark; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(-73, 4); ctx.quadraticCurveTo(0, 10 + open * 20, 73, 4); ctx.stroke();
    ellipse(ctx, -25, -13, 6, 5, animal.dark); ellipse(ctx, 25, -13, 6, 5, animal.dark); ctx.restore();
    return true;
  }
  if (animal.id === "anteater") {
    ctx.save(); ctx.translate(23, 37); ctx.rotate(.18);
    ellipse(ctx, 26, 0, 89, 34, animal.accent); ellipse(ctx, 102, 0, 20, 23, animal.dark);
    if (open > .18) {
      ctx.strokeStyle = "#EF6F91"; ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(104, 6); ctx.lineTo(150 + open * 16, 15); ctx.stroke();
    }
    ctx.restore();
    return true;
  }
  if (animal.id === "tapir") {
    ellipse(ctx, 0, 22, 50, 48, animal.accent); ellipse(ctx, -18, 11, 7, 9, animal.dark); ellipse(ctx, 18, 11, 7, 9, animal.dark);
    ctx.strokeStyle = animal.accent; ctx.lineWidth = 47; ctx.beginPath(); ctx.moveTo(0, 25); ctx.bezierCurveTo(-2, 59, 8, 92, 31 + open * 14, 99); ctx.stroke();
    ctx.strokeStyle = animal.dark; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(17, 99); ctx.quadraticCurveTo(31, 109 + open * 8, 46 + open * 14, 97); ctx.stroke();
    return true;
  }
  if (animal.id === "warthog") {
    ellipse(ctx, 0, 47, 76, 55, animal.accent); ellipse(ctx, -27, 35, 9, 12, animal.dark); ellipse(ctx, 27, 35, 9, 12, animal.dark);
    triangle(ctx, [[-65,48],[-101,102],[-45,65]], "#FFF0CC"); triangle(ctx, [[65,48],[101,102],[45,65]], "#FFF0CC");
    drawMouth(ctx, animal, pose, 80);
    return true;
  }
  if (animal.id === "buffalo") {
    ellipse(ctx, 0, 48, 79, 56, animal.accent); ellipse(ctx, -29, 33, 9, 12, animal.dark); ellipse(ctx, 29, 33, 9, 12, animal.dark);
    drawMouth(ctx, animal, pose, 81);
    return true;
  }
  if (animal.id === "camel") {
    ellipse(ctx, 0, 43, 62, 60, animal.accent); ellipse(ctx, -22, 22, 8, 11, animal.dark); ellipse(ctx, 22, 22, 8, 11, animal.dark);
    drawMouth(ctx, animal, pose, 73);
    if (open > .44) { ctx.fillStyle = "#FFF7D9"; ctx.fillRect(-20, 66, 17, 20); ctx.fillRect(3, 66, 17, 20); }
    return true;
  }
  if (animal.id === "beaver") {
    ellipse(ctx, 0, 41, 59, 48, animal.accent); ellipse(ctx, 0, 22, 19, 13, animal.dark);
    drawMouth(ctx, animal, pose, 70);
    ctx.fillStyle = "#FFF8DE"; ctx.fillRect(-23, 56, 21, 31 + open * 9); ctx.fillRect(2, 56, 21, 31 + open * 9);
    ctx.strokeStyle = animal.dark; ctx.lineWidth = 4; ctx.strokeRect(-23, 56, 46, 31 + open * 9);
    return true;
  }
  if (["rooster", "turkey", "puffin", "cockatoo", "ostrich"].includes(animal.id)) {
    if (animal.id === "puffin") {
      triangle(ctx, [[-70,19],[0,-8],[70,19]], "#F39A3C");
      triangle(ctx, [[-67,23],[0,60 + surprised * 22],[67,23]], "#E65348");
      ctx.strokeStyle = "#FFE25F"; ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(-39,17); ctx.lineTo(43,17); ctx.stroke();
    } else if (animal.id === "ostrich") {
      ellipse(ctx, 0, 30, 63, 33, "#E69E67");
      triangle(ctx, [[-58,30],[0,78 + surprised * 18],[58,30]], "#C87554");
    } else {
      const beak = animal.id === "cockatoo" ? "#555267" : "#F2B23B";
      triangle(ctx, [[-39,24],[0,-6],[39,24]], beak);
      triangle(ctx, [[-35,28],[0,59 + surprised * 18],[35,28]], animal.id === "cockatoo" ? "#353341" : "#D27A31");
      if (["rooster", "turkey"].includes(animal.id)) {
        ellipse(ctx, 10, 61 + surprised * 9, 18, 38 + surprised * 8, animal.accent);
      }
    }
    return true;
  }
  if (animal.id === "squid") {
    ellipse(ctx, 0, 46, 23 + open * 11, 16 + open * 28, animal.dark);
    if (open > .3) ellipse(ctx, 0, 59 + open * 9, 11, 7, "#FF8FBA");
    return true;
  }
  if (animal.id === "lobster") {
    ellipse(ctx, 0, 47, 25 + open * 9, 14 + open * 27, animal.dark);
    if (open > .3) ellipse(ctx, 0, 60, 12, 7, "#FF8497");
    return true;
  }
  if (animal.id === "seahorse") {
    ctx.save(); ctx.translate(31, 36); ctx.rotate(.1);
    ellipse(ctx, 31, 0, 75, 27 + open * 7, animal.accent); ellipse(ctx, 99, 0, 17 + open * 7, 17 + open * 10, animal.dark);
    if (open > .35) ellipse(ctx, 104, 0, 8 + open * 7, 8 + open * 7, "#FF86A6"); ctx.restore();
    return true;
  }
  if (animal.id === "stingray") {
    ellipse(ctx, 0, 45 + open * 8, 39 + open * 9, 12 + open * 27, animal.dark);
    if (open > .35) ellipse(ctx, 0, 56 + open * 13, 20, 8, "#FF8FA8");
    return true;
  }
  if (animal.id === "pufferfish") {
    strokeEllipse(ctx, 0, 46, 28 + open * 12, 18 + open * 17, "#F47F8E", 13);
    if (open > .28) ellipse(ctx, 0, 47 + open * 7, 15 + open * 5, 11 + open * 7, animal.dark);
    return true;
  }
  if (animal.id === "bumblebee") {
    ellipse(ctx, -18, 37, 34, 30, animal.accent); ellipse(ctx, 18, 37, 34, 30, animal.accent);
    strokeEllipse(ctx, 0, 39, 53, 39, "rgba(61,51,43,.3)", 5);
    ellipse(ctx, 0, 29, 8, 7, animal.dark);
    if (open > .06) {
      ellipse(ctx, 0, 54 + open * 6, 22 + open * 9, 7 + open * 25, animal.dark);
      if (open > .3) ellipse(ctx, 0, 64 + open * 12, 16 + open * 3, 6 + open * 7, "#FF7794");
      if (open > .68) {
        ellipse(ctx, -8, 47, 8, 6, "#FFFBEA"); ellipse(ctx, 8, 47, 8, 6, "#FFFBEA");
      }
    } else {
      ctx.beginPath(); ctx.moveTo(-24, 54); ctx.quadraticCurveTo(0, 72 + pose.smile * 7, 24, 54);
      ctx.strokeStyle = animal.dark; ctx.lineWidth = 6; ctx.stroke();
      ellipse(ctx, -27, 54, 4, 4, animal.dark); ellipse(ctx, 27, 54, 4, 4, animal.dark);
    }
    return true;
  }
  if (["butterfly", "ladybug", "mantis"].includes(animal.id)) {
    const mouthWidth = animal.id === "mantis" ? 39 : animal.id === "butterfly" ? 44 : 34;
    ellipse(ctx, 0, 48 + open * 7, mouthWidth, 12 + open * 24, animal.dark);
    if (open > .28) ellipse(ctx, 0, 57 + open * 10, mouthWidth * .55, 6 + open * 7, "#FF85A2");
    return true;
  }
  if (animal.id === "snail") {
    ctx.strokeStyle = animal.dark; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(-46,45); ctx.quadraticCurveTo(0,72 + pose.smile * 13 + open * 15,46,45); ctx.stroke();
    if (open > .32) ellipse(ctx,0,59 + open * 8,18 + open * 8,7 + open * 11,"#FF8E9D");
    return true;
  }
  return false;
}

function drawRenderedMask(
  ctx: CanvasRenderingContext2D,
  animal: Animal,
  pose: Pose,
  coverageX: number,
  coverageY: number,
) {
  const sources = RENDERED_MASK_SOURCES[animal.id];
  if (!sources) return false;
  const neutral = loadRenderedMask(sources.neutral);
  const blink = loadRenderedMask(sources.blink);
  const roar = loadRenderedMask(sources.roar);
  const roarMid = sources.roarMid ? loadRenderedMask(sources.roarMid) : null;
  const images = [neutral, blink, roar, ...(sources.roarMid ? [roarMid] : [])];
  if (!images.every((image) => image?.complete && image.naturalWidth > 0)) return false;

  const blinkWeight = clamp(Math.max(pose.blinkLeft, pose.blinkRight) * 1.14);
  const roarWeight = clamp((pose.mouth - .08) * 1.22);
  const blendWeights = getRenderedMaskBlendWeights(blinkWeight, roarWeight, Boolean(sources.roarMid));
  const drawX = -190;
  const drawY = -225;
  const drawSize = 380;
  const blendSurface = getRenderedMaskBlendSurface(drawSize);
  if (!blendSurface) return false;
  const neutralPixels = getRenderedMaskPixels(neutral!, drawSize);
  const blinkPixels = getRenderedMaskPixels(blink!, drawSize);
  const roarPixels = getRenderedMaskPixels(roar!, drawSize);
  const roarMidPixels = roarMid ? getRenderedMaskPixels(roarMid, drawSize) : null;
  if (!neutralPixels || !blinkPixels || !roarPixels || (roarMid && !roarMidPixels)) return false;

  const { canvas: blendCanvas, context: blendCtx } = blendSurface;
  if (!renderedMaskOutput || renderedMaskOutput.width !== drawSize) {
    renderedMaskOutput = blendCtx.createImageData(drawSize, drawSize);
  }
  blendRenderedMaskRgba(
    {
      neutral: neutralPixels,
      blink: blinkPixels,
      roarMid: roarMidPixels,
      roar: roarPixels,
    },
    blendWeights,
    renderedMaskOutput.data,
  );
  blendCtx.putImageData(renderedMaskOutput, 0, 0);

  ctx.save();
  ctx.scale(1, coverageX / coverageY);
  ctx.globalAlpha = 1;
  ctx.drawImage(blendCanvas, drawX, drawY, drawSize, drawSize);
  ctx.shadowColor = "transparent";
  ctx.shadowBlur = 0;
  ctx.shadowOffsetY = 0;
  ctx.restore();
  return true;
}

function drawAnimal(ctx: CanvasRenderingContext2D, animalIndex: number, pose: Pose, time: number) {
  const animal = ANIMALS[animalIndex];
  const bounce = Math.sin(time / 170 + animalIndex) * (2 + pose.smile * 3);
  const surprised = clamp((pose.mouth - 0.2) * 1.2);
  const coverageX = 1.42;
  const coverageY = 1.52;

  ctx.save();
  ctx.translate(pose.x, pose.y + bounce - pose.scale * 8);
  ctx.rotate(pose.angle);
  ctx.scale(pose.scale * coverageX, pose.scale * coverageY);
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.shadowColor = "rgba(31, 19, 46, .26)";
  ctx.shadowBlur = 20;
  ctx.shadowOffsetY = 9;

  if (drawRenderedMask(ctx, animal, pose, coverageX, coverageY)) {
    ctx.restore();
    return;
  }

  if (animal.id === "capybara") {
    ellipse(ctx, -92, -96, 30, 42, animal.dark);
    ellipse(ctx, 92, -96, 30, 42, animal.dark);
    ellipse(ctx, -92, -96, 17, 26, animal.accent);
    ellipse(ctx, 92, -96, 17, 26, animal.accent);
  } else if (animal.id === "frog") {
    ellipse(ctx, -73, -104, 45, 45, animal.color);
    ellipse(ctx, 73, -104, 45, 45, animal.color);
  } else if (animal.id === "pigeon") {
    triangle(ctx, [[-92, -76], [-127, -136], [-42, -105]], animal.dark);
    triangle(ctx, [[92, -76], [127, -136], [42, -105]], animal.dark);
  } else if (animal.id === "raccoon") {
    triangle(ctx, [[-88, -68], [-132, -139], [-36, -108]], animal.dark);
    triangle(ctx, [[88, -68], [132, -139], [36, -108]], animal.dark);
    triangle(ctx, [[-88, -80], [-118, -124], [-51, -103]], animal.accent);
    triangle(ctx, [[88, -80], [118, -124], [51, -103]], animal.accent);
  } else if (animal.id === "axolotl") {
    [-1, 1].forEach((side) => {
      for (let i = 0; i < 3; i += 1) {
        const y = -78 + i * 38;
        ctx.save();
        ctx.translate(side * 106, y);
        ctx.rotate(side * (0.18 + i * 0.12));
        ellipse(ctx, side * 16, 0, 37, 12, i === 1 ? "#FF5E9E" : animal.dark);
        ctx.restore();
      }
    });
  } else if (animal.id === "cow") {
    triangle(ctx, [[-73, -82], [-133, -112], [-101, -40]], animal.color);
    triangle(ctx, [[73, -82], [133, -112], [101, -40]], animal.color);
    ctx.strokeStyle = "#F5C44E";
    ctx.lineWidth = 14;
    ctx.beginPath();
    ctx.moveTo(-74, -105);
    ctx.quadraticCurveTo(-108, -150, -133, -108);
    ctx.moveTo(74, -105);
    ctx.quadraticCurveTo(108, -150, 133, -108);
    ctx.stroke();
  } else if (animal.id === "llama") {
    ellipse(ctx, -62, -121, 24, 63, animal.color);
    ellipse(ctx, 62, -121, 24, 63, animal.color);
    ellipse(ctx, -62, -121, 10, 43, animal.accent);
    ellipse(ctx, 62, -121, 10, 43, animal.accent);
  } else if (animal.id === "otter") {
    ellipse(ctx, -91, -91, 38, 42, animal.dark);
    ellipse(ctx, 91, -91, 38, 42, animal.dark);
    ellipse(ctx, -91, -91, 20, 23, animal.accent);
    ellipse(ctx, 91, -91, 20, 23, animal.accent);
  } else if (animal.id === "tiger") {
    triangle(ctx, [[-88, -68], [-127, -143], [-34, -106]], animal.color);
    triangle(ctx, [[88, -68], [127, -143], [34, -106]], animal.color);
    triangle(ctx, [[-89, -82], [-112, -122], [-52, -104]], animal.accent);
    triangle(ctx, [[89, -82], [112, -122], [52, -104]], animal.accent);
  } else if (animal.id === "goat") {
    ctx.strokeStyle = "#E8BC75";
    ctx.lineWidth = 17;
    ctx.beginPath();
    ctx.moveTo(-65, -104);
    ctx.bezierCurveTo(-103, -152, -133, -138, -124, -102);
    ctx.moveTo(65, -104);
    ctx.bezierCurveTo(103, -152, 133, -138, 124, -102);
    ctx.stroke();
    ellipse(ctx, -88, -89, 29, 38, animal.color);
    ellipse(ctx, 88, -89, 29, 38, animal.color);
  } else {
    drawExtraBack(ctx, animal);
  }

  ctx.shadowBlur = 0;
  const faceX = animal.id === "bumblebee" ? 132 : 124;
  const faceY = animal.id === "bumblebee" ? 126 : 139;
  const faceCenterY = animal.id === "bumblebee" ? -1 : -5;
  ellipse(ctx, 0, faceCenterY, faceX, faceY, animal.color);
  strokeEllipse(ctx, 0, faceCenterY, faceX, faceY, animal.dark, 7);

  if (animal.id === "raccoon") {
    ctx.save();
    ctx.rotate(-0.14);
    ellipse(ctx, -47, -21, 54, 37, animal.dark);
    ctx.restore();
    ctx.save();
    ctx.rotate(0.14);
    ellipse(ctx, 47, -21, 54, 37, animal.dark);
    ctx.restore();
  }
  if (animal.id === "cow") {
    ellipse(ctx, -49, -57, 31, 42, animal.dark);
    ellipse(ctx, 68, 19, 24, 31, animal.dark);
  }
  if (animal.id === "tiger") {
    [-63, 0, 63].forEach((x, i) => {
      triangle(ctx, [[x - 17, -121], [x, -82 + Math.abs(i - 1) * 8], [x + 17, -121]], animal.dark);
    });
    ctx.strokeStyle = animal.dark;
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.moveTo(-108, -18); ctx.lineTo(-73, -4);
    ctx.moveTo(108, -18); ctx.lineTo(73, -4);
    ctx.stroke();
  }
  if (animal.id === "llama") {
    [ -85, -49, -12, 25, 62 ].forEach((x, i) => ellipse(ctx, x, -114 + (i % 2) * 3, 32, 31, i % 2 ? animal.color : animal.accent));
  }
  if (animal.id === "pigeon") {
    ellipse(ctx, 0, 62, 92, 69, animal.accent);
    ellipse(ctx, -79, 17, 32, 70, "#746FD1");
    ellipse(ctx, 79, 17, 32, 70, "#746FD1");
  }
  if (animal.id === "goat") {
    ellipse(ctx, -35, -117, 28, 22, animal.accent);
    ellipse(ctx, 0, -125, 31, 23, animal.accent);
    ellipse(ctx, 35, -117, 28, 22, animal.accent);
  }

  drawExtraDetails(ctx, animal);

  if (animal.id === "bumblebee") {
    drawBumblebeeEye(ctx, -43, -40, pose.blinkLeft, surprised, animal.dark);
    drawBumblebeeEye(ctx, 43, -40, pose.blinkRight, surprised, animal.dark);
  } else {
    const eyeY = animal.id === "frog" ? -50 : animal.id === "owl" ? -32 : animal.id === "mantis" ? -43 : -35;
    const eyeX = animal.id === "frog" ? 72 : ["owl", "chameleon", "mantis", "snail"].includes(animal.id) ? 62 : 48;
    drawEye(ctx, -eyeX, eyeY, pose.blinkLeft, animal.dark, surprised);
    drawEye(ctx, eyeX, eyeY, pose.blinkRight, animal.dark, surprised);
  }

  if (drawExtraMouth(ctx, animal, pose, surprised)) {
    // Extra zoo animals draw their own distinct muzzles, beaks, trunks, and smiles.
  } else if (animal.id === "pigeon") {
    triangle(ctx, [[-39, 30], [0, 2], [39, 30]], "#FFD34D");
    triangle(ctx, [[-39, 31], [0, 54 + surprised * 15], [39, 31]], "#F69B34");
  } else if (animal.id === "frog") {
    ellipse(ctx, -22, 23, 5, 4, animal.dark);
    ellipse(ctx, 22, 23, 5, 4, animal.dark);
    drawMouth(ctx, animal, pose, 62);
  } else {
    if (["capybara", "otter", "raccoon", "tiger"].includes(animal.id)) {
      ellipse(ctx, 0, 38, animal.id === "capybara" ? 58 : 51, animal.id === "capybara" ? 47 : 41, animal.accent);
    }
    if (animal.id === "cow") ellipse(ctx, 0, 46, 73, 47, "#F4A9A1");
    if (animal.id === "llama" || animal.id === "goat") ellipse(ctx, 0, 42, 52, 51, animal.accent);
    if (animal.id === "axolotl") ellipse(ctx, 0, 35, 48, 34, animal.accent);
    ellipse(ctx, 0, 25, animal.id === "cow" ? 15 : 18, animal.id === "cow" ? 10 : 13, animal.dark);
    if (animal.id === "cow") {
      ellipse(ctx, -35, 49, 6, 8, animal.dark);
      ellipse(ctx, 35, 49, 6, 8, animal.dark);
    }
    drawMouth(ctx, animal, pose, animal.id === "cow" ? 79 : 67);
  }

  if (animal.id === "otter") {
    ctx.strokeStyle = animal.accent;
    ctx.lineWidth = 4;
    [-1, 1].forEach((side) => {
      for (let i = -1; i <= 1; i += 1) {
        ctx.beginPath();
        ctx.moveTo(side * 35, 47 + i * 7);
        ctx.lineTo(side * 126, 37 + i * 17);
        ctx.stroke();
      }
    });
  }

  ctx.restore();
}

type GalleryPose = "neutral" | "blink" | "roar";

const GALLERY_POSES: Record<GalleryPose, Omit<Pose, "x" | "y" | "scale" | "angle">> = {
  neutral: { blinkLeft: .03, blinkRight: .03, mouth: .08, smile: .58 },
  blink: { blinkLeft: 1, blinkRight: 1, mouth: .08, smile: .58 },
  roar: { blinkLeft: .04, blinkRight: .04, mouth: 1, smile: .92 },
};

const RENDERED_BASELINES: Partial<Record<string, Record<GalleryPose, string>>> = {
  bumblebee: {
    neutral: "./design/baselines/bumblebee-chibi-neutral-v1.webp",
    blink: "./design/baselines/bumblebee-chibi-blink-v1.webp",
    roar: "./design/baselines/bumblebee-chibi-roar-v1.webp",
  },
};

function DiagnosticSheet({ poseName }: { poseName: GalleryPose }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const columns = 10;
    const cellWidth = 300;
    const cellHeight = 300;
    const rows = Math.ceil(ANIMALS.length / columns);
    canvas.width = columns * cellWidth;
    canvas.height = rows * cellHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let cancelled = false;
    const draw = () => {
      ctx.fillStyle = "#FFF8E8";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ANIMALS.forEach((animal, animalIndex) => {
        const column = animalIndex % columns;
        const row = Math.floor(animalIndex / columns);
        const x = column * cellWidth;
        const y = row * cellHeight;
        ctx.fillStyle = (column + row) % 2 ? "#FFFDF7" : "#F4EBD7";
        ctx.fillRect(x + 6, y + 6, cellWidth - 12, cellHeight - 12);
        ctx.strokeStyle = "rgba(36,25,48,.18)";
        ctx.lineWidth = 3;
        ctx.strokeRect(x + 6, y + 6, cellWidth - 12, cellHeight - 12);
        drawAnimal(ctx, animalIndex, {
          x: x + cellWidth / 2,
          y: y + 142,
          scale: .47,
          angle: 0,
          ...GALLERY_POSES[poseName],
        }, 0);
        ctx.shadowColor = "transparent";
        ctx.fillStyle = "#241930";
        ctx.textAlign = "center";
        ctx.font = "900 15px Arial";
        ctx.fillText(`${String(animalIndex + 1).padStart(2, "0")} · ${animal.name}`, x + cellWidth / 2, y + 276);
      });
    };

    draw();
    Promise.all(preloadRenderedMasks().map((image) => image.decode().catch(() => undefined))).then(() => {
      if (!cancelled) draw();
    });
    return () => { cancelled = true; };
  }, [poseName]);

  const download = () => {
    const canvas = ref.current;
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = `giggle-zoo-${poseName}-${ANIMALS.length}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  };

  return (
    <section className="diagnostic-sheet" data-gallery-pose={poseName}>
      <div className="diagnostic-sheet-heading">
        <div><span>Actual renderer · {ANIMALS.length} / {ANIMALS.length}</span><h2>{poseName} pose</h2></div>
        <button type="button" onClick={download}>Download PNG</button>
      </div>
      <canvas ref={ref} aria-label={`All ${ANIMALS.length} Giggle Zoo masks in the ${poseName} pose`} />
    </section>
  );
}

function DiagnosticSpotlight({ animalIndex, poseName }: { animalIndex: number; poseName: GalleryPose }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    canvas.width = 520;
    canvas.height = 520;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.fillStyle = poseName === "neutral" ? "#FFE058" : poseName === "blink" ? "#31D3B4" : "#FF5B49";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "rgba(255,253,247,.82)";
    ctx.beginPath(); ctx.arc(260, 248, 205, 0, Math.PI * 2); ctx.fill();
    drawAnimal(ctx, animalIndex, {
      x: 260,
      y: 255,
      scale: .78,
      angle: 0,
      ...GALLERY_POSES[poseName],
    }, 0);
  }, [animalIndex, poseName]);

  return (
    <article className="diagnostic-spotlight-card" data-gallery-pose={poseName}>
      <div><span>{poseName === "neutral" ? "Hello" : poseName === "blink" ? "Blink" : "Big roar"}</span><strong>{poseName}</strong></div>
      <canvas ref={ref} aria-label={`${ANIMALS[animalIndex].name} in the ${poseName} pose`} />
    </article>
  );
}

function RenderedSpotlight({ animal, poseName, src }: { animal: Animal; poseName: GalleryPose; src: string }) {
  return (
    <article className="diagnostic-spotlight-card diagnostic-rendered-card" data-gallery-pose={poseName} data-render-source="imagegen">
      <div><span>{poseName === "neutral" ? "Hello" : poseName === "blink" ? "Blink" : "Big roar"}</span><strong>{poseName}</strong></div>
      <img src={src} alt={`${animal.name} rendered in the ${poseName} pose`} />
    </article>
  );
}

function RenderedMaskProof({ animalIndex }: { animalIndex: number }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    preloadRenderedMask(ANIMALS[animalIndex].id);
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    canvas.width = 920;
    canvas.height = 560;
    let frame = 0;
    const start = performance.now();
    const ease = (value: number) => {
      const safe = clamp(value);
      return safe * safe * (3 - 2 * safe);
    };

    const render = (now: number) => {
      const phase = ((now - start) % 7200) / 7200;
      const blinkIn = ease((phase - .18) / .035);
      const blinkOut = 1 - ease((phase - .34) / .055);
      const blink = clamp(Math.min(blinkIn, blinkOut));
      const roarIn = ease((phase - .5) / .13);
      const roarOut = 1 - ease((phase - .82) / .13);
      const mouth = .08 + .92 * clamp(Math.min(roarIn, roarOut));

      const backdrop = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
      backdrop.addColorStop(0, "#31D3B4");
      backdrop.addColorStop(.52, "#FFE058");
      backdrop.addColorStop(1, "#FF7562");
      ctx.fillStyle = backdrop;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "rgba(255,253,247,.58)";
      ctx.beginPath(); ctx.arc(460, 280, 245, 0, Math.PI * 2); ctx.fill();
      drawAnimal(ctx, animalIndex, {
        x: 460,
        y: 304,
        scale: 1.12,
        angle: Math.sin(now / 900) * .025,
        blinkLeft: blink,
        blinkRight: blink,
        mouth,
        smile: .82,
      }, now);
      frame = requestAnimationFrame(render);
    };

    frame = requestAnimationFrame(render);
    return () => cancelAnimationFrame(frame);
  }, [animalIndex]);

  return (
    <section className="runtime-mask-proof" data-runtime-mask={ANIMALS[animalIndex].id}>
      <div><span>Runtime proof</span><strong>Neutral → blink → roar</strong><p>Transparent rendered states, smoothly blended by the same expression inputs used by the live camera.</p></div>
      <canvas ref={ref} aria-label={`${ANIMALS[animalIndex].name} animated rendered-mask transition proof`} />
    </section>
  );
}

function DiagnosticGallery({ focusId }: { focusId?: string }) {
  const focusIndex = focusId ? ANIMALS.findIndex((animal) => animal.id === focusId) : -1;

  if (focusIndex >= 0) {
    const animal = ANIMALS[focusIndex];
    const renderedBaseline = RENDERED_BASELINES[animal.id];
    const renderedMask = RENDERED_MASK_SOURCES[animal.id];
    const renderedStates = renderedBaseline ?? renderedMask;
    return (
      <main className="diagnostic-gallery diagnostic-gallery-focus" data-animal-count={ANIMALS.length} data-focus-animal={animal.id} data-review-source={renderedStates ? "imagegen" : "canvas"}>
        <header>
          <a href="./">← Giggle Zoo!</a>
          <a href="?gallery=1">See all {ANIMALS.length} masks →</a>
        </header>
        <div className="diagnostic-intro">
          <p className="eyebrow"><span>{renderedStates ? "Rendered mask" : "Approval candidate"}</span> {renderedStates ? "ImageGen character states" : "Same renderer as the live camera"}</p>
          <h1>{animal.name}.<br /><em>Three big moods.</em></h1>
          <p>{renderedStates ? "The actual rendered character states used by the live asset-based mask system." : "One character, enlarged for a close look at silhouette, surface detail, eye language, and mouth response before the visual system expands across the whole zoo."}</p>
        </div>
        <section className="diagnostic-spotlight-grid" aria-label={`${animal.name} state comparison`}>
          {renderedStates ? (
            (Object.keys(GALLERY_POSES) as GalleryPose[]).map((poseName) => (
              <RenderedSpotlight key={poseName} animal={animal} poseName={poseName} src={renderedStates[poseName]} />
            ))
          ) : (
            <>
              <DiagnosticSpotlight animalIndex={focusIndex} poseName="neutral" />
              <DiagnosticSpotlight animalIndex={focusIndex} poseName="blink" />
              <DiagnosticSpotlight animalIndex={focusIndex} poseName="roar" />
            </>
          )}
        </section>
        {renderedMask ? <RenderedMaskProof animalIndex={focusIndex} /> : null}
        <section className="diagnostic-approval-note">
          <span>{renderedStates ? "Rendered quality bar" : "What this direction establishes"}</span>
          <p>{renderedStates ? "This animal uses a consistent rendered state set. The live mask layer positions and transitions those assets instead of redrawing them as simplified procedural shapes." : "A chibi-forward species silhouette, oversized expressive eyes, compact plush proportions, layered materials, and reactions that stay cute without losing the character."}</p>
        </section>
      </main>
    );
  }

  return (
    <main className="diagnostic-gallery" data-animal-count={ANIMALS.length}>
      <header>
        <a href="./">← Giggle Zoo!</a>
        <p>Renderer diagnostic · neutral / blink / roar</p>
      </header>
      <div className="diagnostic-intro">
        <p className="eyebrow"><span>Keeper check</span> Same drawing code as the live camera</p>
        <h1>All {ANIMALS.length} faces.<br /><em>Three big moods.</em></h1>
        <p>Every tile below calls the exact canvas mask renderer used on tracked faces. Download a full-resolution sheet for close inspection.</p>
      </div>
      <DiagnosticSheet poseName="neutral" />
      <DiagnosticSheet poseName="blink" />
      <DiagnosticSheet poseName="roar" />
    </main>
  );
}

function DemoMascot() {
  return (
    <div className="demo-mascot" aria-hidden="true">
      <div className="mascot-ear mascot-ear-left" />
      <div className="mascot-ear mascot-ear-right" />
      <div className="mascot-head">
        <div className="mascot-mask mascot-mask-left" />
        <div className="mascot-mask mascot-mask-right" />
        <div className="mascot-eye mascot-eye-left"><i /></div>
        <div className="mascot-eye mascot-eye-right"><i /></div>
        <div className="mascot-muzzle" />
        <div className="mascot-nose" />
        <div className="mascot-smile" />
      </div>
      <div className="mascot-spark spark-one">✦</div>
      <div className="mascot-spark spark-two">✹</div>
    </div>
  );
}

export default function Home() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const screenRef = useRef<HTMLDivElement>(null);
  const cameraShellRef = useRef<HTMLDivElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const landmarkerRef = useRef<FaceLandmarker | null>(null);
  const landmarkerPromiseRef = useRef<Promise<FaceLandmarker> | null>(null);
  const frameRef = useRef<number | null>(null);
  const lastVideoTimeRef = useRef(-1);
  const tracksRef = useRef<FaceTrack[]>([]);
  const nextTrackIdRef = useRef(1);
  const countRef = useRef(0);
  const particlesRef = useRef<Particle[]>([]);
  const featuredAnimalRef = useRef(3);
  const forcedAnimalRef = useRef<number | null>(null);
  const mountedRef = useRef(true);
  const stateRef = useRef<CameraState>("idle");
  const [cameraState, setCameraState] = useState<CameraState>("idle");
  const [faceCount, setFaceCount] = useState(0);
  const [currentAnimal, setCurrentAnimal] = useState(ANIMALS[3].name);
  const [errorMessage, setErrorMessage] = useState("");
  const [shuffleCount, setShuffleCount] = useState(0);
  const [canFullscreen, setCanFullscreen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [diagnosticMode, setDiagnosticMode] = useState<string | null>(null);

  const updateCameraState = useCallback((next: CameraState) => {
    stateRef.current = next;
    if (mountedRef.current) setCameraState(next);
  }, []);

  const ensureLandmarker = useCallback(() => {
    if (landmarkerRef.current) return Promise.resolve(landmarkerRef.current);
    if (landmarkerPromiseRef.current) return landmarkerPromiseRef.current;
    landmarkerPromiseRef.current = (async () => {
      const vision = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm",
      );
      const options = {
        baseOptions: {
          modelAssetPath:
            "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
          delegate: "GPU" as const,
        },
        runningMode: "VIDEO" as const,
        numFaces: 6,
        outputFaceBlendshapes: true,
        minFaceDetectionConfidence: 0.45,
        minFacePresenceConfidence: 0.45,
        minTrackingConfidence: 0.45,
      };
      try {
        const task = await FaceLandmarker.createFromOptions(vision, options);
        landmarkerRef.current = task;
        return task;
      } catch {
        const task = await FaceLandmarker.createFromOptions(vision, {
          ...options,
          baseOptions: { ...options.baseOptions, delegate: "CPU" },
        });
        landmarkerRef.current = task;
        return task;
      }
    })().catch((error) => {
      landmarkerPromiseRef.current = null;
      throw error;
    });
    return landmarkerPromiseRef.current;
  }, []);

  const stopCamera = useCallback((nextState: CameraState = "off") => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    tracksRef.current = [];
    countRef.current = 0;
    setFaceCount(0);
    updateCameraState(nextState);
    const canvas = canvasRef.current;
    canvas?.getContext("2d")?.clearRect(0, 0, canvas.width, canvas.height);
  }, [updateCameraState]);

  const syncCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const screen = screenRef.current;
    if (!canvas || !screen) return { width: 0, height: 0, dpr: 1 };
    const { width, height } = screen.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
    }
    return { width, height, dpr };
  }, []);

  const mapPoint = useCallback((landmark: NormalizedLandmark, width: number, height: number) => {
    const video = videoRef.current;
    if (!video?.videoWidth || !video.videoHeight) return { x: width / 2, y: height / 2 };
    const cover = Math.max(width / video.videoWidth, height / video.videoHeight);
    const renderedWidth = video.videoWidth * cover;
    const renderedHeight = video.videoHeight * cover;
    const xOffset = (width - renderedWidth) / 2;
    const yOffset = (height - renderedHeight) / 2;
    return {
      x: width - (landmark.x * renderedWidth + xOffset),
      y: landmark.y * renderedHeight + yOffset,
    };
  }, []);

  const drawParticles = useCallback((ctx: CanvasRenderingContext2D, now: number) => {
    particlesRef.current = particlesRef.current.filter((particle) => now - particle.born < 1100);
    particlesRef.current.forEach((particle) => {
      const age = (now - particle.born) / 1000;
      const alpha = clamp(1 - age / 1.1);
      const x = particle.x + particle.vx * age;
      const y = particle.y + particle.vy * age + 300 * age * age;
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.translate(x, y);
      ctx.rotate(particle.spin * age);
      ctx.fillStyle = particle.color;
      ctx.fillRect(-5, -9, 10, 18);
      ctx.restore();
    });
  }, []);

  const updateTracks = useCallback((result: FaceLandmarkerResult, now: number, width: number, height: number) => {
    const detections = result.faceLandmarks.map((landmarks, index) => {
      const left = mapPoint(landmarks[234], width, height);
      const right = mapPoint(landmarks[454], width, height);
      const top = mapPoint(landmarks[10], width, height);
      const bottom = mapPoint(landmarks[152], width, height);
      const leftEye = mapPoint(landmarks[33], width, height);
      const rightEye = mapPoint(landmarks[263], width, height);
      const faceWidth = Math.hypot(right.x - left.x, right.y - left.y);
      return {
        x: (top.x + bottom.x) / 2,
        y: (top.y + bottom.y) / 2 - faceWidth * 0.015,
        scale: faceWidth / 218,
        angle: Math.atan2(leftEye.y - rightEye.y, leftEye.x - rightEye.x),
        blinkLeft: categoryScore(result, index, "eyeBlinkLeft"),
        blinkRight: categoryScore(result, index, "eyeBlinkRight"),
        mouth: categoryScore(result, index, "jawOpen"),
        smile: Math.max(categoryScore(result, index, "mouthSmileLeft"), categoryScore(result, index, "mouthSmileRight")),
      };
    });

    const unmatched = new Set(tracksRef.current.map((track) => track.id));
    const updated: FaceTrack[] = [];
    const threshold = Math.max(width, height) * 0.22;

    detections.forEach((pose) => {
      let best: FaceTrack | undefined;
      let bestDistance = Infinity;
      tracksRef.current.forEach((track) => {
        if (!unmatched.has(track.id)) return;
        const distance = Math.hypot(track.pose.x - pose.x, track.pose.y - pose.y);
        if (distance < bestDistance && distance < threshold) {
          best = track;
          bestDistance = distance;
        }
      });

      if (best) {
        unmatched.delete(best.id);
        updated.push({
          ...best,
          lastSeen: now,
          pose: {
            x: mix(best.pose.x, pose.x, 0.38),
            y: mix(best.pose.y, pose.y, 0.38),
            scale: mix(best.pose.scale, pose.scale, 0.28),
            angle: mix(best.pose.angle, pose.angle, 0.34),
            blinkLeft: mix(best.pose.blinkLeft, pose.blinkLeft, 0.55),
            blinkRight: mix(best.pose.blinkRight, pose.blinkRight, 0.55),
            mouth: mix(best.pose.mouth, pose.mouth, 0.42),
            smile: mix(best.pose.smile, pose.smile, 0.35),
          },
        });
      } else {
        const animalIndex = forcedAnimalRef.current ?? randomAnimal();
        preloadRenderedMask(ANIMALS[animalIndex].id);
        updated.push({
          id: nextTrackIdRef.current++,
          animal: animalIndex,
          pose,
          lastSeen: now,
        });
      }
    });

    tracksRef.current.forEach((track) => {
      if (unmatched.has(track.id) && now - track.lastSeen < 420) updated.push(track);
    });
    tracksRef.current = updated;

    const visibleCount = detections.length;
    if (countRef.current !== visibleCount) {
      countRef.current = visibleCount;
      setFaceCount(visibleCount);
    }
    if (updated[0]) {
      featuredAnimalRef.current = updated[0].animal;
      setCurrentAnimal(ANIMALS[updated[0].animal].name);
    }
  }, [mapPoint]);

  const renderFrame = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const landmarker = landmarkerRef.current;
    if (stateRef.current !== "live" || !video || !canvas || !landmarker) return;

    const { width, height, dpr } = syncCanvas();
    const ctx = canvas.getContext("2d");
    const now = performance.now();
    if (ctx && width && height) {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      if (video.readyState >= 2 && video.currentTime !== lastVideoTimeRef.current) {
        lastVideoTimeRef.current = video.currentTime;
        try {
          const result = landmarker.detectForVideo(video, now);
          updateTracks(result, now, width, height);
        } catch {
          // A dropped frame is harmless; the next animation frame retries.
        }
      }
      tracksRef.current.forEach((track) => drawAnimal(ctx, track.animal, track.pose, now));
      drawParticles(ctx, now);
    }
    frameRef.current = requestAnimationFrame(renderFrame);
  }, [drawParticles, syncCanvas, updateTracks]);

  const startCamera = useCallback(async () => {
    if (stateRef.current === "requesting" || stateRef.current === "warming") return;
    setErrorMessage("");
    updateCameraState("requesting");
    if (!navigator.mediaDevices?.getUserMedia) {
      setErrorMessage("This browser can’t open a webcam. Try a current version of Chrome, Edge, or Safari.");
      updateCameraState("error");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 960 } },
        audio: false,
      });
      if (!mountedRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      updateCameraState("warming");
      await ensureLandmarker();
      if (!mountedRef.current || !streamRef.current) return;
      lastVideoTimeRef.current = -1;
      updateCameraState("live");
      frameRef.current = requestAnimationFrame(renderFrame);
    } catch (error) {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      const name = error instanceof DOMException ? error.name : "";
      if (name === "NotAllowedError") {
        setErrorMessage("Camera access is blocked. Allow it in your browser settings, then try again.");
      } else if (name === "NotFoundError") {
        setErrorMessage("No camera was found. Connect one and give it another go.");
      } else if (name === "NotReadableError") {
        setErrorMessage("Another app may be using your camera. Close it there, then retry.");
      } else {
        setErrorMessage("The animal department couldn’t open your camera. Please try again.");
      }
      updateCameraState("error");
    }
  }, [ensureLandmarker, renderFrame, updateCameraState]);

  const shuffle = useCallback(() => {
    let featured = randomAnimal(featuredAnimalRef.current);
    tracksRef.current = tracksRef.current.map((track, index) => {
      const next = randomAnimal(track.animal);
      preloadRenderedMask(ANIMALS[next].id);
      if (index === 0) featured = next;
      return { ...track, animal: next };
    });
    preloadRenderedMask(ANIMALS[featured].id);
    featuredAnimalRef.current = featured;
    setCurrentAnimal(ANIMALS[featured].name);
    setShuffleCount((count) => count + 1);
    const screen = screenRef.current;
    if (screen) {
      const { width, height } = screen.getBoundingClientRect();
      const born = performance.now();
      particlesRef.current.push(...Array.from({ length: 34 }, (_, index) => ({
        x: width / 2,
        y: height * 0.72,
        vx: (Math.random() - 0.5) * 540,
        vy: -180 - Math.random() * 330,
        born,
        color: CONFETTI[index % CONFETTI.length],
        spin: (Math.random() - 0.5) * 14,
      })));
    }
  }, []);

  const toggleFullscreen = useCallback(async () => {
    const shell = cameraShellRef.current;
    if (!shell?.requestFullscreen || !document.fullscreenEnabled) return;
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await shell.requestFullscreen();
      }
    } catch {
      setCanFullscreen(false);
    }
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement === cameraShellRef.current);
    };
    setCanFullscreen(Boolean(document.fullscreenEnabled && cameraShellRef.current?.requestFullscreen));
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setDiagnosticMode(params.get("gallery"));
    const forcedId = params.get("animal");
    const forcedIndex = forcedId ? ANIMALS.findIndex((animal) => animal.id === forcedId) : -1;
    forcedAnimalRef.current = forcedIndex >= 0 ? forcedIndex : null;
    if (forcedIndex >= 0) {
      featuredAnimalRef.current = forcedIndex;
      preloadRenderedMask(ANIMALS[forcedIndex].id);
      setCurrentAnimal(ANIMALS[forcedIndex].name);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    const keydown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (event.code === "Space" && stateRef.current === "live" && target?.tagName !== "BUTTON") {
        event.preventDefault();
        shuffle();
      }
    };
    window.addEventListener("keydown", keydown);
    return () => {
      mountedRef.current = false;
      window.removeEventListener("keydown", keydown);
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      landmarkerRef.current?.close();
    };
  }, [shuffle]);

  const isBusy = cameraState === "requesting" || cameraState === "warming";
  const isLive = cameraState === "live";

  if (diagnosticMode) return <DiagnosticGallery focusId={diagnosticMode === "1" ? undefined : diagnosticMode} />;

  return (
    <main className="site-shell">
      <div className="zoo-canopy canopy-left" aria-hidden="true"><i /><i /><i /><i /></div>
      <div className="zoo-canopy canopy-right" aria-hidden="true"><i /><i /><i /><i /></div>
      <div className="paw-trail" aria-hidden="true"><span>●</span><span>●</span><span>●</span><span>●</span></div>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Giggle Zoo home">
          <span className="brand-burst" aria-hidden="true">🦁</span>
          <span>Giggle</span>
          <strong>Zoo!</strong>
        </a>
        <div className="privacy-pill">
          <span className="privacy-dot" aria-hidden="true" />
          Camera magic stays on this device
        </div>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <div className="admission-sign" aria-hidden="true">Kids enter free · Grown-ups welcome</div>
          <p className="eyebrow"><span>Roar!</span> Welcome to the wildest little zoo</p>
          <h1>Your face just <em>went wild!</em></h1>
          <p className="lede">
            Jump into the picture and meet your surprise animal twin. Blink, grin, and make your biggest roar-face—the zoo follows along!
          </p>
          <div className="hero-cta-row">
            <button className="button button-primary hero-button" type="button" onClick={startCamera} disabled={isBusy || isLive}>
              <span aria-hidden="true">●</span>
              {isBusy ? "Opening the zoo…" : isLive ? "The zoo is open!" : "Meet my animal"}
            </button>
            <p className="microcopy">Grown-up note: no account and no uploads. Everything happens on this device.</p>
          </div>
          <div className="quick-facts" aria-label="Game facts">
            <div><strong>{ANIMALS.length}</strong><span>Silly zoo pals</span></div>
            <div><strong>6</strong><span>Friends at once</span></div>
            <div><strong>0</strong><span>Photos saved</span></div>
          </div>
        </div>

        <div className="game-wrap">
          <div className="habitat-sign camera-habitat-sign" aria-hidden="true"><span>YOU ARE HERE</span> Face Safari</div>
          <div className={`camera-shell state-${cameraState}`} ref={cameraShellRef}>
            <div className="tape tape-top" aria-hidden="true">Keeper-approved silliness</div>
            <div className="camera-hud">
              <div className={`live-badge ${isLive ? "is-live" : ""}`}>
                <span /> {isLive ? "Zoo is open" : "Zoo is snoozing"}
              </div>
              <div className="face-counter" aria-live="polite">
                {isLive ? `${faceCount} ${faceCount === 1 ? "explorer" : "explorers"} spotted` : "Waiting for an explorer"}
              </div>
            </div>

            <div className="camera-screen" ref={screenRef}>
              <video ref={videoRef} className="camera-video" playsInline muted aria-label="Mirrored webcam preview" />
              <canvas ref={canvasRef} className="face-canvas" aria-hidden="true" />

              {!isLive && !isBusy && cameraState !== "error" && (
                <div className="poster-state">
                  <DemoMascot />
                  <p>{cameraState === "off" ? "The zoo is snoozing." : "Which animal will you be?"}</p>
                  <span>{cameraState === "off" ? "Your camera is safely off." : "Put your face in the picture"}</span>
                </div>
              )}

              {isBusy && (
                <div className="loading-state" role="status">
                  <div className="loader-face"><i /><i /></div>
                  <strong>{cameraState === "requesting" ? "Opening the zoo camera…" : "Waking up the animals…"}</strong>
                  <span>{cameraState === "requesting" ? "A grown-up can allow camera permission." : "Your animal pals are almost ready."}</span>
                </div>
              )}

              {cameraState === "error" && (
                <div className="error-state" role="alert">
                  <span className="error-icon" aria-hidden="true">!</span>
                  <strong>The zoo camera needs help</strong>
                  <p>{errorMessage}</p>
                  <button className="button button-small" type="button" onClick={startCamera}>Try again</button>
                </div>
              )}

              {isLive && faceCount === 0 && (
                <div className="find-face" role="status">
                  <span className="corner corner-a" /><span className="corner corner-b" />
                  <span className="corner corner-c" /><span className="corner corner-d" />
                  <strong>Jump into the picture</strong>
                  <small>Your animal pal is looking for you.</small>
                </div>
              )}
            </div>

            <div className="camera-controls">
              {isLive ? (
                <>
                  <button className="button button-shuffle" type="button" onClick={shuffle}>
                    <span aria-hidden="true">↻</span> Meet another animal
                  </button>
                  <button className="button button-quiet" type="button" onClick={() => stopCamera("off")}>
                    <span className="stop-square" aria-hidden="true" /> Close zoo camera
                  </button>
                </>
              ) : (
                <button className="button button-shuffle" type="button" onClick={startCamera} disabled={isBusy}>
                  <span aria-hidden="true">●</span> {isBusy ? "Getting ready…" : cameraState === "off" ? "Wake the zoo up" : "Open the zoo camera"}
                </button>
              )}
              {canFullscreen && (
                <button
                  className="button button-quiet button-fullscreen"
                  type="button"
                  onClick={toggleFullscreen}
                  aria-pressed={isFullscreen}
                >
                  <span className="fullscreen-icon" aria-hidden="true">⛶</span>
                  {isFullscreen ? "Exit full screen" : "Full screen"}
                </button>
              )}
            </div>
            <div className="tape tape-bottom" aria-hidden="true">Big smiles welcome</div>
          </div>

          <div className="animal-ticket" aria-live="polite" key={shuffleCount}>
            <span>Your zoo pal</span>
            <strong>{currentAnimal}</strong>
            <small>{isLive ? "Press space to meet another" : "Open the camera to meet your pal"}</small>
          </div>
        </div>
      </section>

      <section className="habitats" aria-labelledby="habitats-heading">
        <div className="habitats-intro">
          <p className="eyebrow"><span>Zoo map</span> Pick a path, meet a pal</p>
          <h2 id="habitats-heading">Every trail leads to a giggle.</h2>
          <p>Our animal masks come from every corner of the zoo. Who will pop up next?</p>
        </div>
        <div className="habitat-map">
          <article className="habitat-card habitat-savanna">
            <span className="habitat-icon" aria-hidden="true">☀</span><small>Trail 01</small><h3>Sunny Savanna</h3><p>Lion · Giraffe · Okapi · Hyena · Warthog · Buffalo · Camel</p>
          </article>
          <article className="habitat-card habitat-jungle">
            <span className="habitat-icon" aria-hidden="true">❧</span><small>Trail 02</small><h3>Jungle Jamboree</h3><p>Orangutan · Baboon · Anteater · Tapir · Gorilla · Chameleon</p>
          </article>
          <article className="habitat-card habitat-ocean">
            <span className="habitat-icon" aria-hidden="true">≈</span><small>Trail 03</small><h3>Splash Zone</h3><p>Walrus · Platypus · Squid · Lobster · Seahorse · Stingray · Pufferfish</p>
          </article>
          <article className="habitat-card habitat-forest">
            <span className="habitat-icon" aria-hidden="true">▲</span><small>Trail 04</small><h3>Wiggly Woods</h3><p>Porcupine · Skunk · Beaver · Hedgehog · Wolf · Moose · Red Panda</p>
          </article>
          <article className="habitat-card habitat-barnyard">
            <span className="habitat-icon" aria-hidden="true">✿</span><small>Trail 05</small><h3>Friendly Farm</h3><p>Cow · Pig · Goat · Alpaca · Llama · Capybara · Bunny</p>
          </article>
          <article className="habitat-card habitat-aviary">
            <span className="habitat-icon" aria-hidden="true">✦</span><small>Trail 06</small><h3>Feather Fiesta</h3><p>Rooster · Turkey · Puffin · Cockatoo · Ostrich · Parrot · Peacock</p>
          </article>
        </div>
      </section>

      <section className="how-it-works" aria-labelledby="how-heading">
        <div className="section-heading">
          <p className="eyebrow"><span>Three</span> easy-peasy steps</p>
          <h2 id="how-heading">Ready, set, ROAR!</h2>
        </div>
        <div className="steps">
          <article><b>01</b><span className="step-icon">◎</span><h3>Open the zoo</h3><p>A grown-up can allow the camera. We never record, upload, or save what it sees.</p></article>
          <article><b>02</b><span className="step-icon">⌁</span><h3>Make your silliest face</h3><p>Blink, grin, tilt, or roar. Your animal pal copies you in real time.</p></article>
          <article><b>03</b><span className="step-icon">↻</span><h3>Meet the whole zoo</h3><p>Tap the button or press space. You’ll get a different animal every time.</p></article>
        </div>
      </section>

      <div className="marquee" aria-hidden="true">
        <div>{[...ANIMALS, ...ANIMALS].map((animal, index) => <span key={`${animal.id}-${index}`}>{animal.name} ✦ </span>)}</div>
      </div>

      <footer>
        <div><strong>Giggle Zoo!</strong><span>Silly animal magic for curious kids.</span></div>
        <p><span className="privacy-dot" /> Grown-up approved: face detection runs in your browser.</p>
      </footer>
    </main>
  );
}
