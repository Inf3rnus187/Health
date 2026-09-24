import { useState } from 'react';

import type { JournalDay } from '../../api/journalDays';
import { useJournalDays } from '../../hooks/useJournalDays';
import { frNumber, shortDate } from '../../utils/format';
import { type Range, useRange } from '../../utils/range';
import { DateRange } from '../DateRange';
import { PageSize } from '../PageSize';
import { Pager } from '../Pager';
import { goesText, hoursText, spanText, wakesText } from './nightText';

const HEADS = [
  'Jour',
  'Sommeil',
  'En combien de fois',
  'Réveils',
  'Coucher → lever',
  'Eau',
  'Cafés',
  'Cigarettes',
  'Pipi',
  'Repas',
  'Médicaments',
];

const count = (n: number | null) => (n == null ? '—' : frNumber(n, 0));

/** The night's cells: asleep, in how many goes, awakenings, span. */
function nightCells(night: JournalDay['sleep']): string[] {
  if (!night) return ['—', '—', '—', '—'];
  return [
    hoursText(night.asleep_min),
    goesText(night) || '—',
    wakesText(night) || '—',
    spanText(night) || '—',
  ];
}

function mealText(d: JournalDay): string {
  if (!d.meals) return '—';
  const kcal = d.meal_kcal == null ? '' : ` · ${frNumber(d.meal_kcal, 0)} kcal`;
  return `${d.meals}${kcal}`;
}

function medsText(d: JournalDay): string {
  if (!d.meds_taken && !d.meds_skipped) return '—';
  const not = d.meds_skipped ? ` · ${d.meds_skipped} non pris` : '';
  return `${d.meds_taken} pris${not}`;
}

function cells(d: JournalDay): string[] {
  return [
    shortDate(d.date),
    ...nightCells(d.sleep),
    d.water_l == null ? '—' : `${frNumber(d.water_l, 1)} L`,
    count(d.coffee),
    count(d.cigarettes),
    count(d.pee),
    mealText(d),
    medsText(d),
  ];
}

const mean = (values: (number | null | undefined)[]) => {
  const kept = values.filter((v): v is number => v != null);
  return kept.length ? kept.reduce((a, b) => a + b, 0) / kept.length : null;
};

/** « Moyennes » of the days shown, each over the days that have it. */
function Averages({ days }: { days: JournalDay[] }) {
  const of = (pick: (d: JournalDay) => number | null | undefined) =>
    mean(days.map(pick));
  const sleep = of((d) => d.sleep?.asleep_min);
  const parts: [string, number | null, (n: number) => string][] = [
    ['sommeil', sleep, hoursText],
    ['eau', of((d) => d.water_l), (n) => `${frNumber(n, 1)} L`],
    ['cafés', of((d) => d.coffee), (n) => frNumber(n, 1)],
    ['cigarettes', of((d) => d.cigarettes), (n) => frNumber(n, 1)],
    ['pipi', of((d) => d.pee), (n) => frNumber(n, 1)],
  ];
  const text = parts
    .filter(([, value]) => value != null)
    .map(([label, value, show]) => `${label} ${show(value ?? 0)}`);
  if (text.length === 0) return null;
  return <p className="muted">Moyennes de la page : {text.join(' · ')}</p>;
}

/** A day's line (on a phone, a card: each value with its title). */
function Line({ day }: { day: JournalDay }) {
  return (
    <tr>
      {cells(day).map((text, i) => (
        <td key={HEADS[i]} data-label={HEADS[i]}>
          {text}
        </td>
      ))}
    </tr>
  );
}

function Table({ days }: { days: JournalDay[] }) {
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
          {days.map((d) => (
            <Line key={d.date} day={d} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

const narrow = () => window.matchMedia('(max-width: 640px)').matches;

function usePage() {
  const [range, setRange] = useRange(30, 'journal.days');
  // A phone shows each day as a card: fewer per page.
  const [limit, setLimit] = useState(() => (narrow() ? 10 : 50));
  const [offset, setOffset] = useState(0);
  const change = (r: Range) => {
    setRange(r);
    setOffset(0);
  };
  const resize = (size: number) => {
    setLimit(size);
    setOffset(0);
  };
  return { range, change, limit, resize, offset, setOffset };
}

/** One line per day: the night, water, coffee, cigarettes, pee, meals. */
export function JournalDays() {
  const p = usePage();
  const data = useJournalDays(p.range, p.limit, p.offset).data;
  const days = data?.items ?? [];
  return (
    <section className="card">
      <h2>Mon journal</h2>
      <DateRange value={p.range} onChange={p.change} />
      {days.length > 0 && <Averages days={days} />}
      <div className="data-head">
        <PageSize value={p.limit} onChange={p.resize} />
        <Pager
          offset={p.offset}
          limit={p.limit}
          total={data?.total ?? 0}
          onPage={p.setOffset}
        />
      </div>
      <Table days={days} />
    </section>
  );
}
