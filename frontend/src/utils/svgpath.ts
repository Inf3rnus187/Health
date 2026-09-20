function bounds(nums: number[]): [number, number] {
  let lo = Infinity;
  let hi = -Infinity;
  for (const n of nums) {
    if (n < lo) lo = n;
    if (n > hi) hi = n;
  }
  return [lo, hi];
}

/** Build an SVG polyline `points` string from x/y arrays, scaled to fit
 *  a ``w`` × ``h`` box (y is flipped so larger values sit higher). */
export function polyline(
  xs: number[],
  ys: number[],
  w: number,
  h: number,
): string {
  const [minX, maxX] = bounds(xs);
  const [minY, maxY] = bounds(ys);
  const sx = maxX > minX ? w / (maxX - minX) : 0;
  const sy = maxY > minY ? h / (maxY - minY) : 0;
  return xs
    .map((x, i) => {
      const px = ((x - minX) * sx).toFixed(1);
      const py = (h - ((ys[i] ?? 0) - minY) * sy).toFixed(1);
      return `${px},${py}`;
    })
    .join(' ');
}
