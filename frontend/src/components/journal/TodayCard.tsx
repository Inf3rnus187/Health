import type { JournalDay, JournalNight } from '../../api/journalDays';
import { useTally, useToday } from '../../hooks/useJournalDays';
import { frNumber } from '../../utils/format';
import { goesText, hoursText, spanText, wakesText } from './nightText';
import { PeeTimes } from './PeeTimes';

interface Counter {
  metric: string;
  field: 'water_bottles' | 'coffee' | 'cigarettes' | 'pee';
  label: string;
  /** The big number and the line under it. */
  show: (n: number) => [string, string];
}

const plural = (n: number, word: string) =>
  `${frNumber(n, 0)} ${word}${n > 1 ? 's' : ''}`;

const COUNTERS: Counter[] = [
  {
    metric: 'water.bottles_1_5',
    field: 'water_bottles',
    label: '💧 Eau',
    show: (n) => [
      `${frNumber(n * 1.5, 1)} L`,
      plural(n, 'bouteille') + ' 1,5 L',
    ],
  },
  {
    metric: 'habit.coffee',
    field: 'coffee',
    label: '☕ Cafés',
    show: (n) => [frNumber(n, 0), 'aujourd’hui'],
  },
  {
    metric: 'habit.cigarettes',
    field: 'cigarettes',
    label: '🚬 Cigarettes',
    show: (n) => [frNumber(n, 0), 'aujourd’hui'],
  },
  {
    metric: 'elimination.urination',
    field: 'pee',
    label: '🚽 Pipi',
    show: (n) => [frNumber(n, 0), 'heures ci-dessous'],
  },
];

/** Counters a day can be confirmed at zero (« 0 aujourd'hui »). */
const ZERO_OK = ['habit.cigarettes', 'habit.coffee', 'water.bottles_1_5'];

const ZERO_HINT =
  'Confirmer zéro aujourd’hui (sinon le jour compte « sans donnée »)';

function Zero(props: { busy: boolean; onClick: () => void }) {
  return (
    <button
      className="btn ghost"
      title={ZERO_HINT}
      disabled={props.busy}
      onClick={props.onClick}
    >
      0
    </button>
  );
}

/** − (takes one back) and +1; « 0 » confirms a day without any. */
function Steps(props: { c: Counter; value: number; noted: boolean }) {
  const step = useTally();
  const tap = (amount: number) =>
    step.mutate({ metric: props.c.metric, amount });
  const zero = !props.noted && ZERO_OK.includes(props.c.metric);
  return (
    <div className="counter-buttons">
      {zero && <Zero busy={step.isPending} onClick={() => tap(0)} />}
      <button
        className="btn ghost"
        aria-label={`${props.c.label} : retirer 1`}
        disabled={!props.value || step.isPending}
        onClick={() => tap(-1)}
      >
        −
      </button>
      <button className="btn" disabled={step.isPending} onClick={() => tap(1)}>
        +1
      </button>
    </div>
  );
}

function Tile({ c, day }: { c: Counter; day?: JournalDay }) {
  const noted = day?.[c.field] != null;
  const value = day?.[c.field] ?? 0;
  const [big, small] = c.show(value);
  return (
    <div className="counter">
      <span className="counter-label">{c.label}</span>
      <span className="counter-value">{big}</span>
      <span className="muted counter-hint">{small}</span>
      <Steps c={c} value={value} noted={noted} />
    </div>
  );
}

function LastNight({ night }: { night: JournalNight | null }) {
  if (!night) {
    return (
      <p className="muted">
        🌙 Pas de nuit enregistrée (montre, ou saisie dans Travail › Dossier
        travail et santé › Nuits).
      </p>
    );
  }
  const parts = [goesText(night), wakesText(night), spanText(night)];
  return (
    <p className="today-night">
      🌙 Nuit : <strong>{hoursText(night.asleep_min)}</strong> de sommeil{' '}
      {parts.filter(Boolean).join(' · ')}
    </p>
  );
}

/** Today at a glance: last night, and a tap per water, coffee, cigarette. */
export function TodayCard() {
  const day = useToday().data?.items[0];
  return (
    <section className="card">
      <h2>Aujourd’hui</h2>
      <LastNight night={day?.sleep ?? null} />
      <div className="counters">
        {COUNTERS.map((c) => (
          <Tile key={c.metric} c={c} day={day} />
        ))}
      </div>
      <PeeTimes />
    </section>
  );
}
