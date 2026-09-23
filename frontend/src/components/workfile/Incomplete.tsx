import type { IncompleteDay } from '../../api/workfile';
import { useWorkDays } from '../../hooks/useWork';
import { useIncomplete } from '../../hooks/useWorkFile';
import { useStored } from '../../utils/stored';
import { usePaging } from '../Paging';
import { Corrected } from './Corrected';
import { DayCard } from './DayCard';
import { TodoCalendar } from './TodoCalendar';
import { marks, monthEnd, thisMonth, todoDays, yearTo } from './todoCalendar';
import { TodoPanel } from './TodoPanel';
import { Choice } from './fields';

const SHOW: Record<string, string> = {
  all: 'Toutes',
  proof: 'Avec preuve',
  none: 'Sans preuve',
  start: 'Embauche manquante',
  end: 'Débauche manquante',
};

function keep(row: IncompleteDay, show: string): boolean {
  const c = row.context;
  if (show === 'proof' || show === 'none') {
    return c.has_proof === (show === 'proof');
  }
  return show === 'all' || c.missing === show;
}

function Help() {
  return (
    <p className="muted">
      Embauche ou débauche non pointée (montre sans batterie, GPS muet). Pour
      chaque journée : les preuves et traces du jour — « Voir » ouvre le reçu,
      la facture ou la capture dans un onglet pour vérifier le lieu avant de
      choisir, « Détails » montre tout ce qui a été lu —, « Prendre » reprend
      leur heure ; les repères (réveil, premiers / derniers pas, heure
      habituelle) aussi. Ajustez, notez d’où vient l’heure, puis « Compléter ».
      Une erreur se corrige plus bas, dans « Corrigées à la main ».
    </p>
  );
}

const VIEWS = { calendar: 'Calendrier', list: 'Liste' };

function List({ rows }: { rows: IncompleteDay[] }) {
  const { page, bar } = usePaging(rows);
  return (
    <>
      {bar}
      <ul className="day-list">
        {page.map((row) => (
          <DayCard key={row.id} row={row} />
        ))}
      </ul>
    </>
  );
}

/** 12 months, a pastille per day to complete; the day picked on the right. */
function Calendar({ rows }: { rows: IncompleteDay[] }) {
  const [last, setLast] = useStored('work.todo.month', thisMonth());
  const [day, setDay] = useStored('work.todo.day', '');
  const first = `${yearTo(last)[0]}-01`;
  const days = useWorkDays({ start: first, end: monthEnd(last) }).data ?? [];
  return (
    <div className="todo-layout">
      <TodoCalendar
        marks={marks(rows, days)}
        selected={day}
        onSelect={setDay}
        last={last}
        setLast={setLast}
      />
      <TodoPanel
        day={day}
        rows={rows}
        days={todoDays(rows)}
        onSelect={setDay}
      />
    </div>
  );
}

function Views(props: { view: string; set: (v: string) => void }) {
  return (
    <div className="tabs">
      {Object.entries(VIEWS).map(([key, label]) => (
        <button
          key={key}
          className={key === props.view ? 'tab active' : 'tab'}
          onClick={() => props.set(key)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/** Every session with a missing half, with what helps to complete it. */
export function Incomplete() {
  const rows = useIncomplete().data ?? [];
  const [show, setShow] = useStored('work.todo.show', 'all', Object.keys(SHOW));
  const [view, setView] = useStored(
    'work.todo.view',
    'calendar',
    Object.keys(VIEWS),
  );
  const kept = rows.filter((r) => keep(r, show));
  const proofs = rows.filter((r) => r.context.has_proof).length;
  return (
    <section className="card">
      <h2>
        Journées à compléter ({rows.length}, dont {proofs} avec preuve)
      </h2>
      <Help />
      <div className="toolbar">
        <Views view={view} set={setView} />
        <Choice options={SHOW} value={show} onChange={setShow} />
      </div>
      {view === 'calendar' ? <Calendar rows={kept} /> : <List rows={kept} />}
      <Corrected />
    </section>
  );
}
