/**
 * Return normalized source weights for the rendered-mask compositor.
 *
 * The three-state path intentionally preserves the original formula. Packs
 * with a semantic roar bridge use two linear segments so the midpoint is a
 * single, authored image instead of a neutral/roar double exposure.
 *
 * Cream×cavity pixels must not be linearly mixed: that path is what produced
 * the gray-brown second bowl near RGB (149, 87, 46). Use
 * `blendRenderedMaskSample` / `blendRenderedMaskRgba` for RGB.
 *
 * @param {number} blinkWeight
 * @param {number} roarWeight
 * @param {boolean} hasRoarMid
 */
export function getRenderedMaskBlendWeights(blinkWeight, roarWeight, hasRoarMid) {
  if (!hasRoarMid) {
    return {
      neutral: (1 - blinkWeight) * (1 - roarWeight),
      blink: blinkWeight * (1 - roarWeight),
      roarMid: 0,
      roar: roarWeight,
    };
  }

  if (roarWeight <= .5) {
    const roarMid = roarWeight * 2;
    const base = 1 - roarMid;
    return {
      neutral: (1 - blinkWeight) * base,
      blink: blinkWeight * base,
      roarMid,
      roar: 0,
    };
  }

  const roar = (roarWeight - .5) * 2;
  return {
    neutral: 0,
    blink: 0,
    roarMid: 1 - roar,
    roar,
  };
}

export const CAVITY_CHANNEL_MAX = 80;
export const CREAM_CHANNEL_MIN = 160;

const LAYER_OPENNESS = {
  neutral: 0,
  blink: 0,
  roarMid: 1,
  roar: 2,
};

function channelMax(r, g, b) {
  return r > g ? (r > b ? r : b) : (g > b ? g : b);
}

export function isCavitySample(r, g, b, a) {
  return a > 16 && channelMax(r, g, b) < CAVITY_CHANNEL_MAX;
}

export function isCreamSample(r, g, b, a) {
  return a > 16 && channelMax(r, g, b) >= CREAM_CHANNEL_MIN;
}

/**
 * Blend one RGBA sample from the four mask layers.
 *
 * Where a more-open mouth is cocoa and a less-open mouth is cream (or the
 * reverse while dissolving a closed smile), keep the more-open RGB instead of
 * averaging to a gray-brown bowl.
 *
 * @param {{neutral?: number[], blink?: number[], roarMid?: number[], roar?: number[]}} samples
 * @param {{neutral: number, blink: number, roarMid: number, roar: number}} weights
 * @returns {number[]} [r, g, b, a] in 0–255
 */
export function blendRenderedMaskSample(samples, weights) {
  const keys = ["neutral", "blink", "roarMid", "roar"];
  let r = 0;
  let g = 0;
  let b = 0;
  let a = 0;
  let mostOpenKey = null;
  let mostOpenness = -1;

  for (const key of keys) {
    const weight = weights[key] ?? 0;
    if (weight <= 0) continue;
    const sample = samples[key];
    if (!sample) continue;
    const alpha = (sample[3] / 255) * weight;
    r += sample[0] * alpha;
    g += sample[1] * alpha;
    b += sample[2] * alpha;
    a += alpha;
    const openness = LAYER_OPENNESS[key];
    if (openness > mostOpenness) {
      mostOpenness = openness;
      mostOpenKey = key;
    }
  }

  if (a <= 1e-8) return [0, 0, 0, 0];

  const mostOpen = mostOpenKey ? samples[mostOpenKey] : null;
  const usesRoarBridge = (weights.roarMid ?? 0) > 1e-6;
  if (usesRoarBridge && mostOpen) {
    const mostIsCavity = isCavitySample(mostOpen[0], mostOpen[1], mostOpen[2], mostOpen[3]);
    const mostIsCream = isCreamSample(mostOpen[0], mostOpen[1], mostOpen[2], mostOpen[3]);
    if (mostIsCavity || mostIsCream) {
      for (const key of keys) {
        const weight = weights[key] ?? 0;
        if (weight <= 0 || LAYER_OPENNESS[key] >= mostOpenness) continue;
        const sample = samples[key];
        if (!sample) continue;
        const lessIsCavity = isCavitySample(sample[0], sample[1], sample[2], sample[3]);
        const lessIsCream = isCreamSample(sample[0], sample[1], sample[2], sample[3]);
        if ((mostIsCavity && !lessIsCavity) || (mostIsCream && lessIsCavity)) {
          return [mostOpen[0], mostOpen[1], mostOpen[2], Math.min(255, a * 255)];
        }
      }
    }
  }

  return [r / a, g / a, b / a, Math.min(255, a * 255)];
}

/**
 * Blend full-size RGBA buffers with the same cream×cavity rule.
 *
 * @param {{neutral: Uint8ClampedArray, blink: Uint8ClampedArray, roarMid?: Uint8ClampedArray | null, roar: Uint8ClampedArray}} layers
 * @param {{neutral: number, blink: number, roarMid: number, roar: number}} weights
 * @param {Uint8ClampedArray} out
 */
export function blendRenderedMaskRgba(layers, weights, out) {
  const sample = {
    neutral: [0, 0, 0, 0],
    blink: [0, 0, 0, 0],
    roarMid: [0, 0, 0, 0],
    roar: [0, 0, 0, 0],
  };
  for (let index = 0; index < out.length; index += 4) {
    copyPixel(layers.neutral, index, sample.neutral);
    copyPixel(layers.blink, index, sample.blink);
    copyPixel(layers.roar, index, sample.roar);
    if (layers.roarMid) copyPixel(layers.roarMid, index, sample.roarMid);
    else sample.roarMid[0] = sample.roarMid[1] = sample.roarMid[2] = sample.roarMid[3] = 0;
    const blended = blendRenderedMaskSample(sample, weights);
    out[index] = blended[0];
    out[index + 1] = blended[1];
    out[index + 2] = blended[2];
    out[index + 3] = blended[3];
  }
}

function copyPixel(source, index, target) {
  target[0] = source[index];
  target[1] = source[index + 1];
  target[2] = source[index + 2];
  target[3] = source[index + 3];
}


