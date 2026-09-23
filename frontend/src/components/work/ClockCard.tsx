import { useClock, useWorkStats } from '../../hooks/useWork';
import { localToday } from '../../utils/format';
import { clockTime, hm } from './format';

function Buttons({ open }: { open: boolean }) {
  const clock = useClock();
  return (
    <>
      <div className="quick">
        <button
          className="btn"
          disabled={clock.isPending || open}
          onClick={() => clock.mutate('in')}
        >
          Embauche maintenant
        </button>
        <button
          className="btn"
          disabled={clock.isPending || !open}
          onClick={() => clock.mutate('out')}
        >
          Débauche maintenant
        </button>
      </div>
      {clock.error && <p className="error">{clock.error.message}</p>}
    </>
  );
}

/** Clock in / out now, and where the day stands. */
export function ClockCard() {
  const today = localToday();
  const stats = useWorkStats({ start: today, end: today }, 35).data;
  const open = stats?.open ?? null;
  return (
    <section className="card">
      <h2>Travail — aujourd’hui : {hm(stats?.total_hours ?? 0)}</h2>
      <p className="muted">
        {open
          ? `Au travail depuis ${clockTime(open.start_at)}.`
          : 'Pas en poste.'}
      </p>
      <Buttons open={open !== null} />
    </section>
  );
}
