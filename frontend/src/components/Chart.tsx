// The ONE generic chart wrapper (§10.1). Pages never draw charts
// directly; they describe a series and this component renders it, so the
// visual language stays consistent everywhere.
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { SeriesPoint } from '../api/types';

interface ChartProps {
  points: SeriesPoint[];
  color: string;
  label: string;
}

export function Chart({ points, color, label }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={points} margin={{ top: 8, right: 16, left: -8 }}>
        <CartesianGrid stroke="var(--color-grid)" vertical={false} />
        <XAxis dataKey="date_key" fontSize={11} tickMargin={6} />
        <YAxis fontSize={11} width={40} />
        <Tooltip />
        <Line
          type="monotone"
          dataKey="value"
          name={label}
          stroke={color}
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
