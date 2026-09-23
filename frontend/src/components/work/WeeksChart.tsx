/* eslint-disable max-lines-per-function --
   Recharts is declarative; this component is only axis/bar config. */
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { WorkWeek } from '../../api/work';

const MAX_WEEK = 48;
const MARGIN = { top: 8, right: 16, left: -8 };
const OFF: Record<string, string> = {
  arret: 'arrêt',
  conge: 'congés',
  repos: 'repos',
  autre: 'absence',
  ferie: 'férié',
};

function color(week: WorkWeek): string {
  if (week.over_48h) return 'var(--color-danger)';
  if (week.absence === 'arret') return 'var(--color-warn)';
  if (week.absent_days > 0) return 'var(--color-muted)';
  return 'var(--color-primary)';
}

function label(week: string, weeks: WorkWeek[]): string {
  const found = weeks.find((w) => w.week === week);
  if (!found?.absent_days) return week;
  const why = OFF[found.absence ?? ''] ?? 'absence';
  return `${week} — ${found.absent_days} j ${why}, objectif ${found.target} h`;
}

/** Hours per ISO week, the contract line and the 48 h legal maximum;
 * weeks with days off coloured, their reduced target dashed. */
export function WeeksChart(props: { weeks: WorkWeek[]; contract: number }) {
  if (props.weeks.length === 0) {
    return <p className="muted">Aucune heure sur la période.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <ComposedChart data={props.weeks} margin={MARGIN}>
        <CartesianGrid stroke="var(--color-grid)" vertical={false} />
        <XAxis dataKey="week" fontSize={11} />
        <YAxis fontSize={11} width={44} />
        <Tooltip
          formatter={(value: number, name: string) => [`${value} h`, name]}
          labelFormatter={(week: string) => label(week, props.weeks)}
        />
        <ReferenceLine y={props.contract} stroke="var(--color-ok)" />
        <ReferenceLine y={MAX_WEEK} stroke="var(--color-danger)" />
        <Bar dataKey="hours" name="Heures" isAnimationActive={false}>
          {props.weeks.map((week) => (
            <Cell key={week.week} fill={color(week)} />
          ))}
        </Bar>
        <Line
          dataKey="target"
          name="Objectif (absences déduites)"
          type="step"
          stroke="var(--color-ok)"
          strokeDasharray="4 3"
          dot={false}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
