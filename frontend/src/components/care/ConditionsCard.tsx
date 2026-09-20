import { createCondition, deleteCondition } from '../../api/care';
import type { Condition } from '../../api/types';
import { useCareMutation, useConditions } from '../../hooks/useCare';
import { onCreate, type Submit } from './form';

const STATUS: [string, string][] = [
  ['active', 'Active'],
  ['resolved', 'Résolue'],
  ['suspected', 'Suspectée'],
];
const LABEL = Object.fromEntries(STATUS);

function Form({ onSubmit }: { onSubmit: Submit }) {
  return (
    <form className="care-form" onSubmit={onSubmit}>
      <input className="input" name="name" placeholder="Maladie" required />
      <select className="input" name="status" defaultValue="active">
        {STATUS.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <input className="input" name="code" placeholder="Code CIM-10" />
      <button className="btn">Ajouter</button>
    </form>
  );
}

function Row({
  item,
  onDelete,
}: {
  item: Condition;
  onDelete: (id: string) => void;
}) {
  return (
    <li>
      <span className="import-name">{item.name}</span>
      <span className="badge">{LABEL[item.status] ?? item.status}</span>
      {item.code && <span className="muted">{item.code}</span>}
      <button className="btn ghost" onClick={() => onDelete(item.id)}>
        Supprimer
      </button>
    </li>
  );
}

export function ConditionsCard() {
  const items = useConditions().data ?? [];
  const create = useCareMutation('conditions', createCondition);
  const del = useCareMutation('conditions', deleteCondition);
  return (
    <section className="card">
      <h2>Maladies</h2>
      <Form onSubmit={onCreate(create.mutate)} />
      <ul className="care-list">
        {items.map((item) => (
          <Row key={item.id} item={item} onDelete={del.mutate} />
        ))}
      </ul>
    </section>
  );
}
