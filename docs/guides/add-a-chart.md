# Guide — add a chart (governed, no ad‑hoc chart code)

Chart governance (§10.1): pages never draw charts themselves. They show a
metric through the shared components, so the same metric has the same
numbers, colour and chart everywhere (Accueil, Tableaux de bord, Santé,
Données, Dossier, Suivi).

## Show a metric (numbers + chart)

```tsx
import { MetricPanel } from '../components/metric/MetricPanel';

<MetricPanel metricKey="body.weight" />;
<MetricPanel metricKey="bio.hba1c" compact />;   // without the sources line
```

`MetricPanel` reads the metric overview (`GET /metrics/{key}/overview`,
hook `useOverview`): latest reading with its time and source, day value,
7 / 30-day averages, 30-day range, sources — then draws its chart.

## Only the chart

```tsx
import { TrendChart } from '../components/TrendChart';

<TrendChart metricKey="activity.steps" label="Pas" />;
```

`TrendChart` fetches the bucketed series (`GET /trends`, hook `useTrend`),
offers day / week / month / year tabs, takes the metric's colour from the
**semantic palette**
([`theme/palette.ts`](../../frontend/src/theme/palette.ts),
`colorForMetric(key)`) and hands the points to
[`ZoomChart`](../../frontend/src/components/ZoomChart.tsx) (mouse-wheel
time zoom), which renders
[`TrendLines`](../../frontend/src/components/TrendLines.tsx).

Small inline curves (tables, tiles) use
[`Sparkline`](../../frontend/src/components/Sparkline.tsx) (plain SVG).

## Rules

- Do **not** import `recharts` outside `TrendLines.tsx`.
- Colours come from `colorForMetric(key)`, never hard‑coded in a page; to
  change a metric's colour, edit the palette.
- Layout tokens live in [`theme/tokens.ts`](../../frontend/src/theme/tokens.ts)
  and mirror the CSS variables in `styles.css`.
- Colour is never the only carrier of meaning (labels + tooltips too).
