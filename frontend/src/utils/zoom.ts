const DAY_MS = 86_400_000;
const MIN_SPAN = DAY_MS * 2;

/** Return a new [lo, hi] time window zoomed around its centre. deltaY<0
 *  zooms in, deltaY>0 zooms out; the result stays within [min, max]. */
export function zoomDomain(
  domain: [number, number] | null,
  min: number,
  max: number,
  deltaY: number,
): [number, number] {
  const [lo, hi] = domain ?? [min, max];
  const factor = deltaY < 0 ? 0.75 : 1.3333;
  const full = max - min;
  const span = Math.min(full, Math.max((hi - lo) * factor, MIN_SPAN));
  const center = (lo + hi) / 2;
  let nlo = center - span / 2;
  let nhi = center + span / 2;
  if (nlo < min) [nlo, nhi] = [min, min + span];
  if (nhi > max) [nlo, nhi] = [max - span, max];
  return [nlo, nhi];
}
