/* eslint-disable max-lines-per-function --
   Recharts is declarative; this component is only axis/line config. */
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { TrendPoint } from '../api/types';

type TimeDomain = [number, number] | ['dataMin', 'dataMax'];

interface TrendLinesProps {
  points: TrendPoint[];
  color: string;
  label: string;
  domain: TimeDomain;
  fmt: (ms: number) => string;
}

const MARGIN = { top: 8, right: 16, left: -8 };

export function TrendLines({
  points,
  color,
  label,
  domain,
  fmt,
}: TrendLinesProps) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={points} margin={MARGIN}>
        <CartesianGrid stroke="var(--color-grid)" vertical={false} />
        <XAxis
          dataKey="t"
          type="number"
          domain={domain}
          tickFormatter={fmt}
          allowDataOverflow
          fontSize={11}
        />
        <YAxis fontSize={11} width={44} />
        <Tooltip labelFormatter={fmt} />
        <Line
          type="monotone"
          dataKey="value"
          name={label}
          stroke={color}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
