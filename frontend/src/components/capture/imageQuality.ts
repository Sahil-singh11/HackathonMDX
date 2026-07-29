/* Client-side photo pre-check (Lane B).
 *
 * Runs in the browser BEFORE the photo is sent for analysis so an obviously
 * unusable shot can be retaken immediately — this matters offline, where a
 * wasted analyse cycle costs the fisher a queued record and a retake later.
 *
 * This is deliberately a cheap heuristic, not a reimplementation of the
 * server's quality gate (backend/app/services/vision/quality.py). The server
 * remains authoritative; this only catches the blatant cases.
 */

export type PreCheckVerdict = 'ok' | 'dark' | 'bright' | 'blurry'

export interface PreCheckResult {
  verdict: PreCheckVerdict
  /** Mean luma, 0-255. */
  brightness: number
  /** Variance-of-Laplacian style focus score; higher is sharper. */
  sharpness: number
}

/* Thresholds are tuned to only fire on clearly unusable photos. A borderline
 * shot is passed through to the server rather than nagging the fisher. */
const DARK_BELOW = 42
const BRIGHT_ABOVE = 232
const BLUR_BELOW = 55
const SAMPLE_EDGE = 256

/** Downscale to a small square for analysis — full-res decoding on a phone is slow. */
function drawSample(img: HTMLImageElement): ImageData | null {
  const canvas = document.createElement('canvas')
  canvas.width = SAMPLE_EDGE
  canvas.height = SAMPLE_EDGE
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) return null
  ctx.drawImage(img, 0, 0, SAMPLE_EDGE, SAMPLE_EDGE)
  try {
    return ctx.getImageData(0, 0, SAMPLE_EDGE, SAMPLE_EDGE)
  } catch {
    return null // tainted canvas — skip the pre-check rather than blocking the flow
  }
}

function toLuma(data: ImageData): Float32Array {
  const { data: px } = data
  const luma = new Float32Array(px.length / 4)
  for (let i = 0, j = 0; i < px.length; i += 4, j++) {
    luma[j] = 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]
  }
  return luma
}

/** Variance of a 4-neighbour Laplacian — a standard cheap focus measure. */
function laplacianVariance(luma: Float32Array, edge: number): number {
  const responses: number[] = []
  for (let y = 1; y < edge - 1; y++) {
    for (let x = 1; x < edge - 1; x++) {
      const i = y * edge + x
      responses.push(
        4 * luma[i] - luma[i - 1] - luma[i + 1] - luma[i - edge] - luma[i + edge],
      )
    }
  }
  if (responses.length === 0) return 0
  const mean = responses.reduce((a, b) => a + b, 0) / responses.length
  return responses.reduce((acc, r) => acc + (r - mean) ** 2, 0) / responses.length
}

/**
 * Inspect a photo file. Never throws and never blocks the flow: if anything
 * goes wrong (unsupported format, tainted canvas) the verdict is 'ok' and the
 * server's own quality gate does the real work.
 */
export function preCheckPhoto(file: File): Promise<PreCheckResult> {
  return new Promise((resolve) => {
    const fallback: PreCheckResult = { verdict: 'ok', brightness: 0, sharpness: 0 }
    const url = URL.createObjectURL(file)
    const img = new Image()

    img.onload = () => {
      URL.revokeObjectURL(url)
      const sample = drawSample(img)
      if (!sample) return resolve(fallback)

      const luma = toLuma(sample)
      const brightness = luma.reduce((a, b) => a + b, 0) / luma.length
      const sharpness = laplacianVariance(luma, SAMPLE_EDGE)

      let verdict: PreCheckVerdict = 'ok'
      if (brightness < DARK_BELOW) verdict = 'dark'
      else if (brightness > BRIGHT_ABOVE) verdict = 'bright'
      else if (sharpness < BLUR_BELOW) verdict = 'blurry'

      resolve({ verdict, brightness, sharpness })
    }

    img.onerror = () => { URL.revokeObjectURL(url); resolve(fallback) }
    img.src = url
  })
}
