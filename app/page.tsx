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

const ANIMALS: Animal[] = [
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
];

const CONFETTI = ["#FF5B45", "#F8E542", "#64E0B8", "#9E82FF", "#FF8BC2"];

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
  }
}

function drawExtraMouth(ctx: CanvasRenderingContext2D, animal: Animal, pose: Pose, surprised: number) {
  const open = clamp((pose.mouth - 0.08) * 1.55);
  const muzzleIds = ["panda", "lion", "giraffe", "zebra", "fox", "bunny", "dog", "cat", "sloth", "bear", "deer", "unicorn"];
  if (muzzleIds.includes(animal.id)) {
    const wide = ["lion", "bear", "panda"].includes(animal.id);
    ellipse(ctx, 0, 39, wide ? 58 : 49, wide ? 46 : 40, animal.accent);
    ellipse(ctx, 0, 24, animal.id === "bunny" ? 13 : 18, animal.id === "bunny" ? 10 : 13, animal.dark);
    drawMouth(ctx, animal, pose, 68);
    if (["fox", "bunny", "cat"].includes(animal.id)) {
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
    ctx.bezierCurveTo(-2, 60, -2, 99, 26, 104);
    ctx.stroke();
    ctx.strokeStyle = animal.accent;
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.moveTo(-7, 35); ctx.bezierCurveTo(-7, 62, -7, 88, 18, 96); ctx.stroke();
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
  if (animal.id === "flamingo") {
    ellipse(ctx, -3, 34, 43, 27, "#FFD46E");
    ellipse(ctx, 28, 39, 24, 24, animal.dark);
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
  return false;
}

function drawAnimal(ctx: CanvasRenderingContext2D, animalIndex: number, pose: Pose, time: number) {
  const animal = ANIMALS[animalIndex];
  const bounce = Math.sin(time / 170 + animalIndex) * (2 + pose.smile * 3);
  const surprised = clamp((pose.mouth - 0.2) * 1.2);
  const coverageX = 1.26;
  const coverageY = 1.38;

  ctx.save();
  ctx.translate(pose.x, pose.y + bounce - pose.scale * 8);
  ctx.rotate(pose.angle);
  ctx.scale(pose.scale * coverageX, pose.scale * coverageY);
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.shadowColor = "rgba(31, 19, 46, .26)";
  ctx.shadowBlur = 20;
  ctx.shadowOffsetY = 9;

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
  ellipse(ctx, 0, -5, 119, 131, animal.color);

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

  const eyeY = animal.id === "frog" ? -50 : animal.id === "owl" ? -32 : -35;
  const eyeX = animal.id === "frog" ? 72 : ["owl", "chameleon"].includes(animal.id) ? 62 : 48;
  drawEye(ctx, -eyeX, eyeY, pose.blinkLeft, animal.dark, surprised);
  drawEye(ctx, eyeX, eyeY, pose.blinkRight, animal.dark, surprised);

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
  const mountedRef = useRef(true);
  const stateRef = useRef<CameraState>("idle");
  const [cameraState, setCameraState] = useState<CameraState>("idle");
  const [faceCount, setFaceCount] = useState(0);
  const [currentAnimal, setCurrentAnimal] = useState(ANIMALS[3].name);
  const [errorMessage, setErrorMessage] = useState("");
  const [shuffleCount, setShuffleCount] = useState(0);
  const [canFullscreen, setCanFullscreen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

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
        updated.push({
          id: nextTrackIdRef.current++,
          animal: randomAnimal(),
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
      if (index === 0) featured = next;
      return { ...track, animal: next };
    });
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

  return (
    <main className="site-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Giggle Zoo home">
          <span className="brand-burst" aria-hidden="true">✦</span>
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
          <p className="eyebrow"><span>Roar!</span> Welcome to the silliest zoo</p>
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
            <div><strong>35</strong><span>Silly zoo pals</span></div>
            <div><strong>6</strong><span>Friends at once</span></div>
            <div><strong>0</strong><span>Photos saved</span></div>
          </div>
        </div>

        <div className="game-wrap">
          <div className={`camera-shell state-${cameraState}`} ref={cameraShellRef}>
            <div className="tape tape-top" aria-hidden="true">Official zoo business</div>
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
        <div>BUBBLEGUM CAPYBARA ✦ DISCO FROG ✦ PARTY PIGEON ✦ RACCOON RASCAL ✦ HAPPY AXOLOTL ✦ MOO-MOO SUPERSTAR ✦ DRAMA LLAMA ✦ SINGING OTTER ✦ TINY TIGER ✦ BOUNCY GOAT ✦ PANCAKE PANDA ✦ TRUMPET ELEPHANT ✦ SUNSHINE LION ✦ JOLLY GIRAFFE ✦ BANANA MONKEY ✦ CUDDLE KOALA ✦ BUBBLE HIPPO ✦ ZIGZAG ZEBRA ✦ FANTASTIC FOX ✦ HOPSCOTCH BUNNY ✦ PUDDLE PIG ✦ WIGGLE PUPPY ✦ CURIOUS CAT ✦ HOOT-HOOT OWL ✦ WADDLES PENGUIN ✦ SLEEPY SLOTH ✦ HONEY BEAR ✦ TWINKLE DEER ✦ FANCY FLAMINGO ✦ PIRATE PARROT ✦ SUPER SHARK ✦ DISCO OCTOPUS ✦ COLOR-POP CHAMELEON ✦ SPARKLE UNICORN ✦ GRINNING CROCODILE ✦&nbsp;</div>
      </div>

      <footer>
        <div><strong>Giggle Zoo!</strong><span>Silly animal magic for curious kids.</span></div>
        <p><span className="privacy-dot" /> Grown-up approved: face detection runs in your browser.</p>
      </footer>
    </main>
  );
}
