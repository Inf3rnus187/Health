import type { MetricOverview } from '../../api/overview';
import { useOverview } from '../../hooks/useOverview';
import { frNumber, shortDate } from '../../utils/format';
import { sourceLabel } from '../data/sources';
import { TrendChart } from '../TrendChart';

function withUnit(value: number | null | undefined, unit: string | null) {
  if (value == null) {
    return '—';
  }
  return unit ? `${frNumber(value, 2)} ${unit}` : frNumber(value, 2);
}

function when(iso: string | null): string {
  if (!iso) {
    return '';
  }
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) {
    return '';
  }
  const time = at.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
  });
  return ` · ${shortDate(iso)} ${time}`;
}

function Headline({ view }: { view: MetricOverview }) {
  if (!view.latest) {
    return <p className="muted">Aucune valeur enregistrée.</p>;
  }
  return (
    <div className="mp-head">
      <span className="mp-value">{withUnit(view.latest.value, view.unit)}</span>
      <span className="muted">
        Dernier relevé{when(view.latest.at)} · {sourceLabel(view.latest.source)}
      </span>
    </div>
  );
}

function Stats({ view }: { view: MetricOverview }) {
  if (!view.day) {
    return null;
  }
  return (
    <ul className="mp-stats">
      <li>
        {view.day_label} ({shortDate(view.day.date)}) :{' '}
        {withUnit(view.day.value, view.unit)}
      </li>
      <li>Moyenne 7 j : {withUnit(view.avg7, view.unit)}</li>
      <li>Moyenne 30 j : {withUnit(view.avg30, view.unit)}</li>
      <li>
        Min–max 30 j : {withUnit(view.min30, view.unit)} –{' '}
        {withUnit(view.max30, view.unit)}
      </li>
    </ul>
  );
}

function Sources({ view }: { view: MetricOverview }) {
  const sources = view.sources ?? [];
  if (sources.length === 0) {
    return null;
  }
  const text = sources
    .map((s) => `${sourceLabel(s.source)} ${s.count} j`)
    .join(' · ');
  return (
    <p className="muted mp-sources">
      {view.days_count} jours depuis le {shortDate(view.first_day)} — {text}
    </p>
  );
}

interface PanelProps {
  metricKey: string;
  /** Compact: no sources line (dashboards, Santé). */
  compact?: boolean;
}

/** The same numbers and chart for a metric, wherever it is shown. */
export function MetricPanel({ metricKey, compact = false }: PanelProps) {
  const { data, isLoading, error } = useOverview(metricKey);
  if (isLoading) {
    return <p className="muted">Chargement…</p>;
  }
  if (error || !data) {
    return <p className="error">Mesure indisponible.</p>;
  }
  const title = data.unit ? `${data.label} (${data.unit})` : data.label;
  return (
    <div className="dash-card mp">
      <h3 className="dash-title">{title}</h3>
      <Headline view={data} />
      <Stats view={data} />
      {!compact && <Sources view={data} />}
      <TrendChart metricKey={metricKey} label={data.label} />
    </div>
  );
}
