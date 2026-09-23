import { type FormEvent, useState } from 'react';

import {
  createAppointment,
  deleteAppointment,
  importAppointments,
} from '../../api/care';
import type { Appointment } from '../../api/types';
import { useAppointments, useCareMutation } from '../../hooks/useCare';
import { type Selection, useSelection } from '../../hooks/useSelection';
import { shortDateTime } from '../../utils/datetime';
import { useStored } from '../../utils/stored';
import { BulkBar, PickBox } from '../Bulk';
import { usePaging } from '../Paging';
import { onCreate, type Submit } from './form';

const VIEWS = { next: 'À venir', past: 'Passés' };

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

function Row(props: {
  item: Appointment;
  sel: Selection;
  onDelete: (id: string) => void;
}) {
  const { item } = props;
  return (
    <li>
      <PickBox sel={props.sel} id={item.id} />
      <span className="muted nowrap">{shortDateTime(item.starts_at)}</span>
      <span className="import-name">{item.title}</span>
      {item.location && <span className="muted">{item.location}</span>}
      <span className="badge">{item.source}</span>
      <button className="btn ghost" onClick={() => props.onDelete(item.id)}>
        Supprimer
      </button>
    </li>
  );
}

/** Upcoming (soonest first) or past (latest first), matching the search. */
function pick(items: Appointment[], view: string, text: string) {
  const now = Date.now();
  const needle = text.trim().toLowerCase();
  const kept = items.filter((a) => {
    const later = Date.parse(a.starts_at) >= now;
    const said = `${a.title} ${a.location ?? ''}`.toLowerCase();
    return later === (view === 'next') && said.includes(needle);
  });
  const sign = view === 'next' ? 1 : -1;
  return kept.sort(
    (a, b) => sign * (Date.parse(a.starts_at) - Date.parse(b.starts_at)),
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

function List({ items }: { items: Appointment[] }) {
  const del = useCareMutation('appointments', deleteAppointment);
  const sel = useSelection();
  const { page, bar } = usePaging(items);
  const ids = items.map((a) => a.id);
  return (
    <>
      <BulkBar what="appointments" noun="rendez-vous" shown={ids} sel={sel} />
      {bar}
      {items.length === 0 && <p className="muted">Aucun rendez-vous ici.</p>}
      <ul className="care-list">
        {page.map((item) => (
          <Row key={item.id} item={item} sel={sel} onDelete={del.mutate} />
        ))}
      </ul>
    </>
  );
}

/** Add one by hand, or import an agenda (.ics). */
function Adding() {
  const create = useCareMutation('appointments', createAppointment);
  const imp = useCareMutation('appointments', importAppointments);
  return (
    <>
      <Form onSubmit={onCreate(create.mutate)} />
      <ImportForm onImport={imp.mutate} />
    </>
  );
}

/** Appointments: upcoming or past, searchable, a page at a time. */
export function AppointmentsCard() {
  const items = useAppointments().data ?? [];
  const [view, setView] = useStored('care.appointments', 'next', [
    'next',
    'past',
  ]);
  const [text, setText] = useState('');
  return (
    <section className="card">
      <h2>Rendez-vous ({items.length})</h2>
      <Adding />
      <div className="toolbar">
        <Views view={view} set={setView} />
        <input
          className="input"
          placeholder="Chercher (praticien, lieu…)"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </div>
      <List items={pick(items, view, text)} />
    </section>
  );
}
