/**
 * Shared perspective projection.
 *
 * ONE implementation, two configurations: the onboarding bathymetric scene
 * (components/onboarding) and the in-app ambient layer both import from here.
 * It was previously duplicated inside terrain.ts.
 *
 * Rotate about Y (heading), then X (pitch), then divide. No matrix library.
 */

export interface Camera {
  heading: number      // radians, rotation about Y
  pitch: number        // radians, rotation about X (negative looks down)
  dist: number         // world units in front of the camera
  height: number       // camera elevation above the z = 0 plane
  f: number            // focal length in px
  cx: number
  cy: number
}

export interface Projected { x: number; y: number; depth: number }

/**
 * `depth` is returned with the point so callers can fade by distance. That
 * opacity ramp is what actually sells the third dimension — more than the
 * projection itself does.
 */
export function project(x: number, y: number, z: number, c: Camera): Projected {
  const ch = Math.cos(c.heading), sh = Math.sin(c.heading)
  const rx = x * ch - y * sh
  const ry = x * sh + y * ch

  const gz = ry + c.dist      // distance in front of the camera
  const gy = z - c.height     // height relative to the camera

  const cp = Math.cos(c.pitch), sp = Math.sin(c.pitch)
  const py = gy * cp - gz * sp
  const pz = gy * sp + gz * cp

  const denom = Math.max(0.06, pz)
  return { x: c.cx + (rx * c.f) / denom, y: c.cy + (py * c.f) / denom, depth: denom }
}

/** Focal length for a vertical field of view, in radians. */
export const focalFor = (viewportHeight: number, fov: number) =>
  (viewportHeight / 2) / Math.tan(fov / 2)
