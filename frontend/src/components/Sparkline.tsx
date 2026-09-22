const W = 120;
const H = 28;

type Domain = [number, number];

function path(values: number[], domain?: Domain): string {
  const min = domain ? domain[0] : Math.min(...values);
  const max = domain ? domain[1] : Math.max(...values);
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

/** `domain` pins the vertical scale; by default it fits the values. */
export function Sparkline({
  values,
  color,
  domain,
}: {
  values: number[];
  color: string;
  domain?: Domain;
}) {
  if (values.length < 2) {
    return null;
  }
  return (
    <svg className="spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <path
        d={path(values, domain)}
        fill="none"
        stroke={color}
        strokeWidth={2}
      />
    </svg>
  );
}
