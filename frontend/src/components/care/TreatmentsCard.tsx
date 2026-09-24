import {
  createTreatment,
  deleteTreatment,
  updateTreatment,
} from '../../api/care';
import type { Adherence } from '../../api/medications';
import type { Treatment } from '../../api/types';
import { useCareMutation, useTreatments } from '../../hooks/useCare';
import { useAdherence } from '../../hooks/useMedications';
import { frNumber } from '../../utils/format';
import { lastDays } from '../../utils/range';
import { onCreate, type Submit } from './form';

interface RowProps {
  item: Treatment;
  seen?: Adherence;
  onToggle: (item: Treatment) => void;
  onDelete: (id: string) => void;
}

/** « 30 j : 93 % (56/60) · 2 jours sans rien · vers 08:10 ». */
function adherenceText(a: Adherence | undefined): string {
  if (!a || (!a.taken && !a.planned)) return '';
  const rate =
    a.rate == null
      ? `${a.taken} prises`
      : `${frNumber(a.rate, 0)} % (${a.taken}/${a.planned})`;
  const holes = a.days_without_record
    ? ` · ${a.days_without_record} j sans rien noté`
    : '';
  const time = a.usual_time ? ` · vers ${a.usual_time}` : '';
  return `30 j : ${rate}${holes}${time}`;
}

function Form({ onSubmit }: { onSubmit: Submit }) {
  return (
    <form className="care-form" onSubmit={onSubmit}>
      <input className="input" name="name" placeholder="Traitement" required />
      <input className="input" name="dose" placeholder="Dose" />
      <input className="input" name="frequency" placeholder="Fréquence" />
      <input
        className="input"
        name="doses_per_day"
        type="number"
        min={1}
        max={12}
        placeholder="Prises / jour"
        title="Nombre de prises prévues par jour (pour l’observance)"
      />
      <button className="btn">Ajouter</button>
    </form>
  );
}

function toggleBody(item: Treatment): Record<string, unknown> {
  return {
    name: item.name,
    dose: item.dose,
    frequency: item.frequency,
    doses_per_day: item.doses_per_day,
    start_date: item.start_date,
    end_date: item.end_date,
    active: !item.active,
    notes: item.notes,
  };
}

function Row({ item, seen, onToggle, onDelete }: RowProps) {
  const perDay = item.doses_per_day ? `${item.doses_per_day}/jour` : '';
  const desc = [item.dose, item.frequency, perDay].filter(Boolean).join(' · ');
  const kept = adherenceText(seen);
  return (
    <li>
      <span className="import-name">{item.name}</span>
      {desc && <span className="muted">{desc}</span>}
      {kept && <span className="muted small">{kept}</span>}
      <span className={item.active ? 'badge badge-done' : 'badge'}>
        {item.active ? 'Actif' : 'Arrêté'}
      </span>
      <button className="btn ghost" onClick={() => onToggle(item)}>
        {item.active ? 'Arrêter' : 'Reprendre'}
      </button>
      <button className="btn ghost" onClick={() => onDelete(item.id)}>
        Supprimer
      </button>
    </li>
  );
}

function useTreatmentActions() {
  const create = useCareMutation('treatments', createTreatment);
  const del = useCareMutation('treatments', deleteTreatment);
  const upd = useCareMutation('treatments', (t: Treatment) =>
    updateTreatment(t.id, toggleBody(t)),
  );
  return { create, del, upd };
}

export function TreatmentsCard() {
  const items = useTreatments().data ?? [];
  const seen = useAdherence(lastDays(30)).data?.items ?? [];
  const { create, del, upd } = useTreatmentActions();
  return (
    <section className="card">
      <h2>Traitements</h2>
      <Form onSubmit={onCreate(create.mutate)} />
      <ul className="care-list">
        {items.map((item) => (
          <Row
            key={item.id}
            item={item}
            seen={seen.find((a) => a.treatment_id === item.id)}
            onToggle={upd.mutate}
            onDelete={del.mutate}
          />
        ))}
      </ul>
    </section>
  );
}
