import type {
  Bucket,
  MealSpending as Spending,
  SpendKind,
  SpendVendor,
} from '../../api/spending';
import { useMealSpending } from '../../hooks/useSpending';
import { money, shortDate } from '../../utils/format';
import { useRange } from '../../utils/range';
import { useStored } from '../../utils/stored';
import { DateRange } from '../DateRange';
import { Choice } from '../workfile/fields';
import { HoursChart, PeriodChart } from './SpendingCharts';
import { periodLabel } from './spendingLabels';

const KINDS: Record<SpendKind, string> = {
  livraison: 'Livraisons (Uber Eats…)',
  repas: 'Repas payés (reçus, restaurants)',
  tout: 'Livraisons et repas payés',
};
const BUCKETS: Record<Bucket, string> = {
  auto: 'Auto',
  day: 'Par jour',
  week: 'Par semaine',
  month: 'Par mois',
};
const PER: Record<string, string> = {
  day: 'par jour',
  week: 'par semaine',
  month: 'par mois',
};

const euros = (n: number | null | undefined) =>
  n == null ? '—' : `${money(n)} €`;

function tiles(d: Spending): [string, string, string][] {
  const big = d.largest;
  return [
    ['Total dépensé', euros(d.total), `du ${shortDate(d.start)}`],
    ['Commandes', String(d.count), ''],
    ['Panier moyen', euros(d.average), ''],
    ['Moyenne par mois', euros(d.per_month), ''],
    [
      'Plus grosse commande',
      euros(big?.amount),
      big ? `${big.name}, ${shortDate(big.at)}` : '',
    ],
    [
      'Commandes tard (21 h – 5 h)',
      String(d.late.count),
      d.count
        ? `${Math.round((d.late.count / d.count) * 100)} % · ` +
          euros(d.late.total)
        : '',
    ],
  ];
}

function Tiles({ data }: { data: Spending }) {
  return (
    <div className="tiles tiles-wide">
      {tiles(data).map(([label, value, hint]) => (
        <div key={label} className="tile">
          <span className="tile-label muted">{label}</span>
          <span className="tile-value">{value}</span>
          {hint && <span className="tile-date muted">{hint}</span>}
        </div>
      ))}
    </div>
  );
}

const HEADS = ['Établissement', 'Commandes', 'Total', 'Part'];

function Vendors({ rows }: { rows: SpendVendor[] }) {
  return (
    <div className="table-wrap">
      <table className="data-table stack-table">
        <thead>
          <tr>
            {HEADS.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((v) => (
            <tr key={v.name}>
              <td data-label={HEADS[0]}>{v.name}</td>
              <td data-label={HEADS[1]}>{v.count}</td>
              <td data-label={HEADS[2]}>{euros(v.total)}</td>
              <td data-label={HEADS[3]}>{v.share.toLocaleString('fr-FR')} %</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The periods as a table (the chart's values, readable without it). */
function PeriodTable({ data }: { data: Spending }) {
  const spent = data.periods.filter((p) => p.count > 0);
  return (
    <details>
      <summary>Voir le détail {PER[data.bucket]}</summary>
      <ul className="care-list">
        {spent.map((p) => (
          <li key={p.start}>
            {periodLabel(p.start, data.bucket, true)} : {euros(p.total)} (
            {p.count} commande{p.count > 1 ? 's' : ''})
          </li>
        ))}
      </ul>
    </details>
  );
}

function Legend() {
  return (
    <p className="muted chart-legend">
      <span className="swatch" style={{ background: 'var(--chart-1)' }} />{' '}
      Commandes en journée{' '}
      <span className="swatch" style={{ background: 'var(--chart-2)' }} /> Tard
      le soir (21 h – 5 h)
    </p>
  );
}

function Charts({ data }: { data: Spending }) {
  if (data.count === 0) {
    return <p className="muted">Aucune commande sur la période.</p>;
  }
  return (
    <>
      <h3>Dépensé {PER[data.bucket]}</h3>
      <PeriodChart data={data} />
      <PeriodTable data={data} />
      <h3>Heure de commande</h3>
      <HoursChart hours={data.hours} />
      <Legend />
      <h3>Les établissements qui coûtent le plus</h3>
      <Vendors rows={data.vendors} />
    </>
  );
}

function useFilters() {
  const [range, setRange] = useRange(365, 'work.spending');
  const [kind, setKind] = useStored<SpendKind>(
    'work.spending.kind',
    'livraison',
    Object.keys(KINDS),
  );
  const [bucket, setBucket] = useStored<Bucket>(
    'work.spending.bucket',
    'auto',
    Object.keys(BUCKETS),
  );
  return { range, setRange, kind, setKind, bucket, setBucket };
}

/** What Uber Eats and other meals paid for cost, over a period. */
export function MealSpending() {
  const f = useFilters();
  const data = useMealSpending(f.range, f.kind, f.bucket).data;
  return (
    <section className="card">
      <h2>Dépenses repas — Uber Eats et livraisons</h2>
      <DateRange value={f.range} onChange={f.setRange} />
      <div className="toolbar">
        <Choice
          options={KINDS}
          value={f.kind}
          onChange={(v) => f.setKind(v as SpendKind)}
        />
        <Choice
          options={BUCKETS}
          value={f.bucket}
          onChange={(v) => f.setBucket(v as Bucket)}
        />
      </div>
      {data && <Tiles data={data} />}
      {data && <Charts data={data} />}
    </section>
  );
}
