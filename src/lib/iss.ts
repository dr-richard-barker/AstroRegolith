// Estimated ISS ground track from a timestamp.
//
// The ExoLab-11 images were taken aboard the ISS, so they carry no GPS. This is
// a *simplified* spherical circular-orbit ground-track model: given a time it
// returns the sub-satellite lat/long. The latitude band (±inclination) and the
// ~93-minute period are physically correct; the absolute longitude depends on an
// ascending-node anchor we don't have precisely, so treat positions as
// ILLUSTRATIVE estimates, not precise fixes. Good enough to show "these frames
// were somewhere along this orbital band," not for navigation.

const DEG = Math.PI / 180;
const INC = 51.64 * DEG;          // ISS orbital inclination
const PERIOD = 5576.5;            // s, one orbit (~92.9 min)
const WE = 360 / 86164.0905;      // deg/s, Earth's sidereal rotation
// Reference ascending node (2024-11-01T00:00:00Z, longitude 0). Unanchored, so
// absolute longitude is approximate; latitude/shape are correct.
const T0 = 1730419200;
const LON0 = 0;

export interface LatLng { lat: number; lng: number; }

const norm180 = (d: number) => ((d + 180) % 360 + 360) % 360 - 180;

// Sub-satellite point for a unix time (seconds).
export function issPosition(unixSec: number): LatLng {
  const dt = unixSec - T0;
  const u = 2 * Math.PI * (dt / PERIOD);                 // argument of latitude
  const lat = Math.asin(Math.sin(INC) * Math.sin(u)) / DEG;
  const dlon = Math.atan2(Math.cos(INC) * Math.sin(u), Math.cos(u)) / DEG;
  const lng = norm180(LON0 + dlon - WE * dt);
  return { lat, lng };
}

// A ground-track polyline over `durationSec` from `startUnix`, split into
// segments wherever it crosses the ±180° date line (so it can be drawn cleanly).
export function issTrack(startUnix: number, durationSec = PERIOD * 1.6, stepSec = 45): LatLng[][] {
  const segs: LatLng[][] = [];
  let cur: LatLng[] = [];
  let prev: LatLng | null = null;
  for (let t = 0; t <= durationSec; t += stepSec) {
    const p = issPosition(startUnix + t);
    if (prev && Math.abs(p.lng - prev.lng) > 180) { segs.push(cur); cur = []; }
    cur.push(p);
    prev = p;
  }
  if (cur.length) segs.push(cur);
  return segs;
}

export const ISS_INCLINATION = 51.64;
