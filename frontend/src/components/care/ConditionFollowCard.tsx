import { Link } from 'react-router-dom';

import type { MetricOverview } from '../../api/overview';
import type { CareCondition } from '../../api/record';
import { useCareOverview } from '../../hooks/useRecord';
import { colorForMetric } from '../../theme/palette';
import { frNumber, shortDate, signed } from '../../utils/format';
import { DocLinks } from '../record/DocLink';
import { Sparkline } from '../Sparkline';

const STATUS: Record<string, string> = {
  active: 'Active',
  resolved: 'Résolue',
  suspected: 'Suspectée',
};

function Change({ metric }: { metric: MetricOverview }) {
  const first = metric.series[0];
  const last = metric.series[metric.series.length - 1];
  if (!first || !last || first.date === last.date) {
    return null;
  }
  const unit = metric.unit ? ` ${metric.unit}` : '';
  return (
    <span className="muted">
      {signed(last.value - first.value, 2)}
      {unit} depuis le {shortDate(first.date)}
    </span>
  );
}

function Indicator({ metric }: { metric: MetricOverview }) {
  const latest = metric.latest;
  if (!latest) {
    return null;
  }
  const when = latest.at ?? metric.day?.date;
  return (
    <li className="follow-tile">
      <Link to={`/donnees?metric=${encodeURIComponent(metric.key)}`}>
        {metric.label}
      </Link>
      <strong>
        {frNumber(latest.value, 2)} {metric.unit ?? ''}
      </strong>
      <span className="muted">{shortDate(when)}</span>
      <Change metric={metric} />
      <Sparkline
        values={metric.series.map((p) => p.value)}
        color={colorForMetric(metric.key)}
      />
    </li>
  );
}

function Condition({ item }: { item: CareCondition }) {
  return (
    <article className="follow-condition">
      <h3>
        {item.name}{' '}
        <span className="badge">{STATUS[item.status] ?? item.status}</span>
      </h3>
      {item.indicators.length === 0 ? (
        <p className="muted">Pas encore de valeur pour ses indicateurs.</p>
      ) : (
        <ul className="follow-grid">
          {item.indicators.map((metric) => (
            <Indicator key={metric.key} metric={metric} />
          ))}
        </ul>
      )}
      {item.documents.length > 0 && (
        <p className="muted">
          Documents : <DocLinks docs={item.documents} />
        </p>
      )}
    </article>
  );
}

/** Each declared condition with the indicators that follow it. */
export function ConditionFollowCard() {
  const items = useCareOverview().data ?? [];
  return (
    <section className="card">
      <h2>Suivi par maladie</h2>
      <p className="muted">
        Chaque maladie déclarée avec ses indicateurs (Apple Santé, prises de
        sang, FibroScan, saisies) et les documents qui la mentionnent.
      </p>
      {items.length === 0 && (
        <p className="muted">
          Déclarez une maladie ci-dessous (ou confirmez une suggestion lue dans
          vos documents) pour voir ses indicateurs ici.
        </p>
      )}
      {items.map((item) => (
        <Condition key={item.id} item={item} />
      ))}
    </section>
  );
}
