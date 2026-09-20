import {
  createTreatment,
  deleteTreatment,
  updateTreatment,
} from '../../api/care';
import type { Treatment } from '../../api/types';
import { useCareMutation, useTreatments } from '../../hooks/useCare';
import { onCreate, type Submit } from './form';

interface RowProps {
  item: Treatment;
  onToggle: (item: Treatment) => void;
  onDelete: (id: string) => void;
}

function Form({ onSubmit }: { onSubmit: Submit }) {
  return (
    <form className="care-form" onSubmit={onSubmit}>
      <input className="input" name="name" placeholder="Traitement" required />
      <input className="input" name="dose" placeholder="Dose" />
      <input className="input" name="frequency" placeholder="Fréquence" />
      <button className="btn">Ajouter</button>
    </form>
  );
}

function toggleBody(item: Treatment): Record<string, unknown> {
  return {
    name: item.name,
    dose: item.dose,
    frequency: item.frequency,
    start_date: item.start_date,
    end_date: item.end_date,
    active: !item.active,
    notes: item.notes,
  };
}

function Row({ item, onToggle, onDelete }: RowProps) {
  const desc = [item.dose, item.frequency].filter(Boolean).join(' · ');
  return (
    <li>
      <span className="import-name">{item.name}</span>
      {desc && <span className="muted">{desc}</span>}
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

export function TreatmentsCard() {
  const items = useTreatments().data ?? [];
  const create = useCareMutation('treatments', createTreatment);
  const del = useCareMutation('treatments', deleteTreatment);
  const upd = useCareMutation('treatments', (t: Treatment) =>
    updateTreatment(t.id, toggleBody(t)),
  );
  return (
    <section className="card">
      <h2>Traitements</h2>
      <Form onSubmit={onCreate(create.mutate)} />
      <ul className="care-list">
        {items.map((item) => (
          <Row
            key={item.id}
            item={item}
            onToggle={upd.mutate}
            onDelete={del.mutate}
          />
        ))}
      </ul>
    </section>
  );
}
