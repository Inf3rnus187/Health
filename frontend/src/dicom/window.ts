import type { DicomImage } from './parse';

export function autoWindow(image: DicomImage): { wc: number; ww: number } {
  const { pixels, slope, intercept } = image;
  let lo = Infinity;
  let hi = -Infinity;
  for (const raw of pixels) {
    const value = raw * slope + intercept;
    if (value < lo) lo = value;
    if (value > hi) hi = value;
  }
  const ww = Math.max(1, hi - lo);
  return { wc: lo + ww / 2, ww };
}

export function toImageData(
  image: DicomImage,
  wc: number,
  ww: number,
): ImageData {
  const { rows, cols, pixels, slope, intercept, invert } = image;
  const data = new Uint8ClampedArray(rows * cols * 4);
  const lo = wc - ww / 2;
  let offset = 0;
  for (const raw of pixels) {
    const gray = shade(raw * slope + intercept, lo, ww, invert);
    data[offset] = gray;
    data[offset + 1] = gray;
    data[offset + 2] = gray;
    data[offset + 3] = 255;
    offset += 4;
  }
  return new ImageData(data, cols, rows);
}

function shade(value: number, lo: number, ww: number, invert: boolean): number {
  let gray = ((value - lo) / ww) * 255;
  if (gray < 0) gray = 0;
  else if (gray > 255) gray = 255;
  return invert ? 255 - gray : gray;
}
