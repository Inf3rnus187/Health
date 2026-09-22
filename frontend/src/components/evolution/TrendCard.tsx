import type { AngleTrend } from '../../api/evolution';
import { useTrend } from '../../hooks/useEvolution';
import { shortDate } from '../../utils/format';
import { angleLabel } from '../photos/labels';
import { TrendRow } from './TrendRow';

function validCount(trend: AngleTrend): string {
  const noun = trend.photos_valid > 1 ? 'photos valides' : 'photo valide';
  return `${trend.photos_valid} ${noun} / ${trend.photos_total}`;
}

function AngleHead({ trend }: { trend: AngleTrend }) {
  return (
    <div className="trend-angle-head">
      <h3>{angleLabel(trend.angle)}</h3>
      <span className="muted">{validCount(trend)}</span>
      <span className="muted">
        Référence : {shortDate(trend.baseline?.date)} · Dernière :{' '}
        {shortDate(trend.latest?.date)}
      </span>
    </div>
  );
}

function AngleBlock({ trend }: { trend: AngleTrend }) {
  return (
    <div className="trend-angle">
      <AngleHead trend={trend} />
      {trend.criteria.length === 0 ? (
        <p className="muted">Aucun score pour cet angle.</p>
      ) : (
        <ul className="trend-list">
          {trend.criteria.map((criterion) => (
            <TrendRow key={criterion.key} criterion={criterion} />
          ))}
        </ul>
      )}
    </div>
  );
}

function TrendBody() {
  const { data, isLoading, error } = useTrend();
  if (isLoading) {
    return <p className="muted">Chargement…</p>;
  }
  if (error || !data) {
    const why = error ? ` : ${error.message}` : '';
    return <p className="error">Tendance indisponible{why}.</p>;
  }
  return (
    <>
      <p className="muted trend-method">Méthode {data.method_version}</p>
      {data.angles.map((trend) => (
        <AngleBlock key={trend.angle} trend={trend} />
      ))}
    </>
  );
}

export function TrendCard() {
  return (
    <section className="card">
      <h2>Évolution par angle</h2>
      <TrendBody />
      <p className="trend-help muted">
        Score 0–10 (plus haut = plus de graisse abdominale visible). Médiane
        glissante 7 jours, pente robuste (Theil–Sen) sur 90 jours, tendance
        affichée seulement avec ≥ 8 photos valides sur ≥ 21 jours.
      </p>
    </section>
  );
}
