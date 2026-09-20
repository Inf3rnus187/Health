import type { FormEvent } from 'react';

import {
  createAppointment,
  deleteAppointment,
  importAppointments,
} from '../../api/care';
import type { Appointment } from '../../api/types';
import { useAppointments, useCareMutation } from '../../hooks/useCare';
import { shortDateTime } from '../../utils/datetime';
import { onCreate, type Submit } from './form';

interface RowProps {
  item: Appointment;
  onDelete: (id: string) => void;
}

function Form({ onSubmit }: { onSubmit: Submit }) {
  return (
    <form className="care-form" onSubmit={onSubmit}>
      <input
        className="input"
        name="title"
        placeholder="Motif / praticien"
        required
      />
      <input
        className="input"
        type="datetime-local"
        name="starts_at"
        required
      />
      <input className="input" name="location" placeholder="Lieu" />
      <button className="btn">Ajouter</button>
    </form>
  );
}

function ImportForm({ onImport }: { onImport: (form: FormData) => void }) {
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    onImport(new FormData(form));
    form.reset();
  };
  return (
    <form className="care-form" onSubmit={submit}>
      <input className="input" type="file" name="file" accept=".ics" required />
      <button className="btn ghost">Importer .ics (Apple Agenda)</button>
    </form>
  );
}

function Row({ item, onDelete }: RowProps) {
  return (
    <li>
      <span className="import-name">{item.title}</span>
      <span className="muted">{shortDateTime(item.starts_at)}</span>
      {item.location && <span className="muted">{item.location}</span>}
      <span className="badge">{item.source}</span>
      <button className="btn ghost" onClick={() => onDelete(item.id)}>
        Supprimer
      </button>
    </li>
  );
}

export function AppointmentsCard() {
  const items = useAppointments().data ?? [];
  const create = useCareMutation('appointments', createAppointment);
  const del = useCareMutation('appointments', deleteAppointment);
  const imp = useCareMutation('appointments', importAppointments);
  return (
    <section className="card">
      <h2>Rendez-vous</h2>
      <Form onSubmit={onCreate(create.mutate)} />
      <ImportForm onImport={imp.mutate} />
      <ul className="care-list">
        {items.map((item) => (
          <Row key={item.id} item={item} onDelete={del.mutate} />
        ))}
      </ul>
    </section>
  );
}
