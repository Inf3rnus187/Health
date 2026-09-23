/* eslint-disable max-lines-per-function --
   Recharts is declarative; this component is only axis/bar config. */
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { WorkWeek } from '../../api/work';

const MAX_WEEK = 48;
const MARGIN = { top: 8, right: 16, left: -8 };

/** Hours per ISO week, the contract line and the 48 h legal maximum. */
export function WeeksChart(props: { weeks: WorkWeek[]; contract: number }) {
  if (props.weeks.length === 0) {
    return <p className="muted">Aucune heure sur la période.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={props.weeks} margin={MARGIN}>
        <CartesianGrid stroke="var(--color-grid)" vertical={false} />
        <XAxis dataKey="week" fontSize={11} />
        <YAxis fontSize={11} width={44} />
        <Tooltip formatter={(value: number) => [`${value} h`, 'Heures']} />
        <ReferenceLine y={props.contract} stroke="var(--color-ok)" />
        <ReferenceLine y={MAX_WEEK} stroke="var(--color-danger)" />
        <Bar dataKey="hours" isAnimationActive={false}>
          {props.weeks.map((week) => (
            <Cell
              key={week.week}
              fill={
                week.over_48h ? 'var(--color-danger)' : 'var(--color-primary)'
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
