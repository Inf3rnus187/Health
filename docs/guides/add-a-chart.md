# Guide — add a chart (governed, no ad‑hoc chart code)

Chart governance (§10.1): there is **one** generic chart component. Pages
never draw charts directly — they *describe* a series and the component
renders it, so the same metric is always the same colour, everywhere.

## Describe a series

A dashboard series is a declarative descriptor
([`SeriesSpec`](../../frontend/src/api/types.ts)):

```ts
const WEIGHT_SPEC: SeriesSpec = {
  metricKey: 'body.weight',
  agg: 'avg',
  window: 7,
  label: 'Poids (moyenne 7 j)',
};
```

## Render it

```tsx
import { MetricChart } from '../components/MetricChart';

<MetricChart spec={WEIGHT_SPEC} />;
```

`MetricChart` fetches the rolling series with the `useSeries` hook, picks the
metric's colour from the **semantic palette**
([`theme/palette.ts`](../../frontend/src/theme/palette.ts)) and hands the
points to the single [`Chart`](../../frontend/src/components/Chart.tsx)
wrapper. To keep one colour per metric/domain, edit the palette — not the
chart.

## Rules

- Do **not** import `recharts` outside `Chart.tsx`.
- Colours come from `colorForMetric(key)`, never hard‑coded in a page.
- Layout tokens live in [`theme/tokens.ts`](../../frontend/src/theme/tokens.ts)
  and mirror the CSS variables in `styles.css`.
- Colour is never the only carrier of meaning (labels + tooltips too).
