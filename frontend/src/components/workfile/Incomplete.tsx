import type { IncompleteDay } from '../../api/workfile';
import { useIncomplete } from '../../hooks/useWorkFile';
import { useStored } from '../../utils/stored';
import { usePaging } from '../Paging';
import { Corrected } from './Corrected';
import { DayCard } from './DayCard';
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

/** Every session with a missing half, with what helps to complete it. */
export function Incomplete() {
  const rows = useIncomplete().data ?? [];
  const [show, setShow] = useStored('work.todo.show', 'all', Object.keys(SHOW));
  const { page, bar } = usePaging(rows.filter((r) => keep(r, show)));
  const proofs = rows.filter((r) => r.context.has_proof).length;
  return (
    <section className="card">
      <h2>
        Journées à compléter ({rows.length}, dont {proofs} avec preuve)
      </h2>
      <Help />
      <Choice options={SHOW} value={show} onChange={setShow} />
      {bar}
      <ul className="day-list">
        {page.map((row) => (
          <DayCard key={row.id} row={row} />
        ))}
      </ul>
      <Corrected />
    </section>
  );
}
