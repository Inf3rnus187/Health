/* eslint-disable max-lines-per-function --
   Recharts is declarative; these components are only axis/bar config. */
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { MealSpending, SpendHour, SpendPeriod } from '../../api/spending';
import { money } from '../../utils/format';
import { periodLabel } from './spendingLabels';

const MARGIN = { top: 8, right: 8, left: -8 };
const TICK = { fill: 'var(--color-muted)', fontSize: 11 };
/** Thin bars: 4 px rounded top, square on the baseline. */
const BAR = {
  maxBarSize: 24,
  radius: [4, 4, 0, 0] as [number, number, number, number],
};
function orders(count: number): string {
  return `${count} commande${count > 1 ? 's' : ''}`;
}

/** What was spent per day, week or month (empty periods at 0). */
export function PeriodChart({ data }: { data: MealSpending }) {
  const rows = data.periods.map((p: SpendPeriod) => ({
    ...p,
    label: periodLabel(p.start, data.bucket),
  }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={rows} margin={MARGIN} barCategoryGap={2}>
        <CartesianGrid stroke="var(--color-grid)" vertical={false} />
        <XAxis dataKey="label" tick={TICK} interval="preserveStartEnd" />
        <YAxis tick={TICK} width={52} unit=" €" />
        <Tooltip
          cursor={{ fill: 'var(--color-grid)' }}
          formatter={(value: number, _name, item) => [
            `${money(value)} € · ${orders(item.payload.count)}`,
            'Dépensé',
          ]}
          labelFormatter={(_label, items) =>
            items?.[0]
              ? periodLabel(items[0].payload.start, data.bucket, true)
              : ''
          }
        />
        <Bar
          dataKey="total"
          fill="var(--chart-1)"
          isAnimationActive={false}
          {...BAR}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** How many orders at each hour of the day; late ones (21 h – 5 h) apart. */
export function HoursChart({ hours }: { hours: SpendHour[] }) {
  const rows = hours.map((h) => ({ ...h, label: `${h.hour} h` }));
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={rows} margin={MARGIN} barCategoryGap={2}>
        <CartesianGrid stroke="var(--color-grid)" vertical={false} />
        <XAxis dataKey="label" tick={TICK} interval={2} />
        <YAxis tick={TICK} width={40} allowDecimals={false} />
        <Tooltip
          cursor={{ fill: 'var(--color-grid)' }}
          formatter={(value: number, _name, item) => [
            `${orders(value)} · ${money(item.payload.total)} €`,
            item.payload.late ? 'Tard (21 h – 5 h)' : 'Commandes',
          ]}
          labelFormatter={(_label, items) => {
            const hour = items?.[0]?.payload.hour ?? 0;
            return `De ${hour}:00 à ${hour}:59`;
          }}
        />
        <Bar dataKey="count" isAnimationActive={false} {...BAR}>
          {rows.map((h) => (
            <Cell
              key={h.hour}
              fill={h.late ? 'var(--chart-2)' : 'var(--chart-1)'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
