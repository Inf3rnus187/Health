const DAY_MS = 86_400_000;
const MIN_SPAN = DAY_MS * 2;
const LEFT_PAD = 44;
const RIGHT_PAD = 20;

/** Fraction (0..1) of the plot width under the cursor, so zooming can
 *  keep the point under the pointer fixed. */
export function cursorFraction(
  el: HTMLElement | null,
  clientX: number,
): number {
  if (!el) {
    return 0.5;
  }
  const rect = el.getBoundingClientRect();
  const left = rect.left + LEFT_PAD;
  const width = rect.width - LEFT_PAD - RIGHT_PAD;
  if (width <= 0) {
    return 0.5;
  }
  return Math.min(1, Math.max(0, (clientX - left) / width));
}

/** Return a new [lo, hi] window, zoomed around the cursor fraction.
 *  deltaY<0 zooms in, deltaY>0 out; the result stays within [min, max]. */
export function zoomDomain(
  domain: [number, number] | null,
  min: number,
  max: number,
  deltaY: number,
  anchor: number,
): [number, number] {
  const [lo, hi] = domain ?? [min, max];
  const factor = deltaY < 0 ? 0.75 : 1.3333;
  const full = max - min;
  const span = Math.min(full, Math.max((hi - lo) * factor, MIN_SPAN));
  const focus = lo + anchor * (hi - lo);
  let nlo = focus - anchor * span;
  let nhi = nlo + span;
  if (nlo < min) [nlo, nhi] = [min, min + span];
  if (nhi > max) [nlo, nhi] = [max - span, max];
  return [nlo, nhi];
}
