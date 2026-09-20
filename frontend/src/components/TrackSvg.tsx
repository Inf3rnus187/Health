import { polyline } from '../utils/svgpath';

export function TrackSvg({ points }: { points: [number, number][] }) {
  if (points.length === 0) {
    return <p className="muted">Tracé vide.</p>;
  }
  const lat = points.map((point) => point[0]);
  const mean = lat.reduce((sum, value) => sum + value, 0) / lat.length;
  const factor = Math.cos((mean * Math.PI) / 180);
  const xs = points.map((point) => point[1] * factor);
  const path = polyline(xs, lat, 320, 320);
  return (
    <svg viewBox="0 0 320 320" className="track">
      <polyline
        points={path}
        fill="none"
        stroke="var(--color-primary)"
        strokeWidth={2}
      />
    </svg>
  );
}
