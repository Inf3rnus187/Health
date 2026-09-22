import type {
  WeightChange,
  WeightStatus,
  WeightTrend,
} from '../../api/evolution';
import { useTrend } from '../../hooks/useEvolution';
import { frNumber, shortDate, signed } from '../../utils/format';
import { Sparkline } from '../Sparkline';

const STATUS_LABEL: Record<WeightStatus, string> = {
  insufficient: 'Données insuffisantes',
  stable: 'Stable',
  losing: 'En baisse',
  gaining: 'En hausse',
};

// Reuse the trend colours: losing weight is the improvement here.
const TONE: Record<WeightStatus, string> = {
  insufficient: 'insufficient',
  stable: 'stable',
  losing: 'improving',
  gaining: 'worsening',
};

function Headline({ weight }: { weight: WeightTrend }) {
  const tone = TONE[weight.status];
  const slope = weight.slope_30d;
  return (
    <div className="weight-head">
      <span className="marker-value">{frNumber(weight.latest.value)} kg</span>
      <span className="muted">
        Dernière pesée {shortDate(weight.latest.date)}
      </span>
      <span>Moyenne 7 jours : {frNumber(weight.current)} kg</span>
      <span className={`badge st st-${tone}`}>
        {STATUS_LABEL[weight.status]}
      </span>
      {slope !== null && <span>Pente : {signed(slope)} kg / 30 j</span>}
    </div>
  );
}

function changeText(change: WeightChange): string {
  if (change.delta === null || change.percent === null) {
    return 'pas de pesée à cette date';
  }
  return `${signed(change.delta)} kg (${signed(change.percent)} %)`;
}

function Changes({ weight }: { weight: WeightTrend }) {
  return (
    <ul className="weight-changes">
      {weight.changes.map((change) => (
        <li key={change.label}>
          <span className="muted">Sur {change.label} :</span>{' '}
          {changeText(change)}
        </li>
      ))}
    </ul>
  );
}

function Milestones({ weight }: { weight: WeightTrend }) {
  const { value, date } = weight.peak;
  const peak = `${frNumber(value)} kg le ${shortDate(date)}`;
  return (
    <div className="weight-milestones">
      <p>
        Perte depuis le pic des 12 derniers mois ({peak}) :{' '}
        <strong>{frNumber(weight.loss_from_peak_pct)} %</strong>
      </p>
      <ul>
        {weight.milestones.map((step) => (
          <li key={step.percent} className={step.reached ? 'reached' : ''}>
            {step.reached ? '✓' : '○'} −{step.percent} % : {step.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

function WeightBody({ weight }: { weight: WeightTrend }) {
  const values = weight.smoothed.map((point) => point.value);
  return (
    <>
      <Headline weight={weight} />
      <div className={`trend-spark weight-spark st-${TONE[weight.status]}`}>
        <Sparkline values={values} color="currentColor" />
      </div>
      <p className="muted marker-small">
        {weight.n} jours de pesée sur 12 mois · historique depuis le{' '}
        {shortDate(weight.first.date)} ({frNumber(weight.first.value)} kg)
      </p>
      <Changes weight={weight} />
      <Milestones weight={weight} />
    </>
  );
}

function WeightContent() {
  const { data, isLoading, error } = useTrend();
  if (isLoading) {
    return <p className="muted">Chargement…</p>;
  }
  if (error) {
    return <p className="error">Poids indisponible : {error.message}.</p>;
  }
  if (!data?.weight) {
    return <p className="muted">Aucune pesée enregistrée.</p>;
  }
  return <WeightBody weight={data.weight} />;
}

export function WeightCard() {
  return (
    <section className="card">
      <h2>Poids</h2>
      <WeightContent />
      <p className="disclaimer">
        Toutes les pesées enregistrées (Apple Santé, Health Auto Export, saisie)
        : médiane glissante 7 jours, pente robuste sur 90 jours. Paliers de
        perte de poids des recommandations européennes sur la stéatose (EASL
        2024) et de l’étude DiRECT pour le diabète de type 2.
      </p>
    </section>
  );
}
