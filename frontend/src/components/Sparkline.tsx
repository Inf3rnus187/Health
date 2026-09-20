const W = 120;
const H = 28;

function path(values: number[]): string {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = values.length > 1 ? W / (values.length - 1) : W;
  return values
    .map((v, i) => {
      const x = i * step;
      const y = H - ((v - min) / span) * H;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}

export function Sparkline({
  values,
  color,
}: {
  values: number[];
  color: string;
}) {
  if (values.length < 2) {
    return null;
  }
  return (
    <svg className="spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <path d={path(values)} fill="none" stroke={color} strokeWidth={2} />
    </svg>
  );
}
