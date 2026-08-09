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
  } else {
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

  const eyeY = animal.id === "frog" ? -50 : -35;
  const eyeX = animal.id === "frog" ? 72 : 48;
  drawEye(ctx, -eyeX, eyeY, pose.blinkLeft, animal.dark, surprised);
  drawEye(ctx, eyeX, eyeY, pose.blinkRight, animal.dark, surprised);

  if (animal.id === "pigeon") {
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
            <div><strong>10</strong><span>Silly zoo pals</span></div>
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
        <div>BUBBLEGUM CAPYBARA ✦ DISCO FROG ✦ MOO-MOO SUPERSTAR ✦ PARTY PIGEON ✦ DRAMA LLAMA ✦ SINGING OTTER ✦ RACCOON RASCAL ✦&nbsp;</div>
      </div>

      <footer>
        <div><strong>Giggle Zoo!</strong><span>Silly animal magic for curious kids.</span></div>
        <p><span className="privacy-dot" /> Grown-up approved: face detection runs in your browser.</p>
      </footer>
    </main>
  );
}
