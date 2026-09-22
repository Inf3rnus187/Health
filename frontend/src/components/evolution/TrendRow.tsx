import type { TrendCriterion, TrendStatus } from '../../api/evolution';
import { frNumber, signed } from '../../utils/format';
import { Sparkline } from '../Sparkline';

const STATUS_LABEL: Record<TrendStatus, string> = {
  insufficient: 'Données insuffisantes',
  stable: 'Stable',
  improving: 'En amélioration',
  worsening: 'En aggravation',
};

// Keep at least MIN_SPAN points of vertical scale (clamped to the 0–10
// score range) so day-to-day noise isn't stretched to full height.
const MIN_SPAN = 2;

function sparkDomain(values: number[]): [number, number] {
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const pad = Math.max(0, (MIN_SPAN - (hi - lo)) / 2);
  return [Math.max(0, lo - pad), Math.min(10, hi + pad)];
}

function signedOrDash(value: number | null, unit: string): string {
  return value === null ? '—' : `${signed(value, 2)} ${unit}`;
}

function Spark({ criterion }: { criterion: TrendCriterion }) {
  const values = criterion.smoothed.map((point) => point.value);
  return (
    <div className={`trend-spark st-${criterion.status}`}>
      {values.length >= 2 ? (
        <Sparkline
          values={values}
          color="currentColor"
          domain={sparkDomain(values)}
        />
      ) : (
        <span className="muted">—</span>
      )}
    </div>
  );
}

function Stats({ criterion }: { criterion: TrendCriterion }) {
  const last = criterion.smoothed.at(-1);
  return (
    <div className="trend-stats">
      <span>Actuel : {last ? `${frNumber(last.value)}/10` : '—'}</span>
      <span>Pente : {signedOrDash(criterion.slope_30d, 'pt / 30 j')}</span>
      <span>
        Depuis la référence : {signedOrDash(criterion.baseline_delta, 'pt')}
      </span>
      <span className="muted">
        n = {criterion.n} sur {criterion.span_days} j
      </span>
    </div>
  );
}

export function TrendRow({ criterion }: { criterion: TrendCriterion }) {
  return (
    <li className="trend-row">
      <div className="trend-name">
        <span>{criterion.label}</span>
        <span className={`badge st st-${criterion.status}`}>
          {STATUS_LABEL[criterion.status] ?? criterion.status}
        </span>
      </div>
      <Spark criterion={criterion} />
      <Stats criterion={criterion} />
    </li>
  );
}
