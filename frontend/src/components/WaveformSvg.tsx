import { polyline } from '../utils/svgpath';

export function WaveformSvg({ values }: { values: number[] }) {
  if (values.length === 0) {
    return <p className="muted">Trace vide.</p>;
  }
  const xs = values.map((_, index) => index);
  const path = polyline(xs, values, 1000, 200);
  return (
    <svg viewBox="0 0 1000 200" preserveAspectRatio="none" className="wave">
      <polyline
        points={path}
        fill="none"
        stroke="var(--color-danger)"
        strokeWidth={1}
      />
    </svg>
  );
}
