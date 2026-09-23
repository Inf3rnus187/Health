import { useState } from 'react';

import {
  EVIDENCE_KINDS,
  type EvidenceItem,
  TRACE_KINDS,
} from '../../api/workfile';
import { type Selection, useSelection } from '../../hooks/useSelection';
import { useDeleteEvidence, useEvidence } from '../../hooks/useWorkFile';
import { useRange } from '../../utils/range';
import { useStored } from '../../utils/stored';
import { BulkBar, PickBox } from '../Bulk';
import { DateRange } from '../DateRange';
import { usePaging } from '../Paging';
import { EvidenceFile } from '../FileButtons';
import { EvidenceViewer } from './EvidenceViewer';
import { span, viewable } from './evidenceView';
import { Choice } from './fields';

const SHOW: Record<string, string> = {
  all: 'Tout',
  proof: 'Preuves',
  trace: 'Traces',
  ...EVIDENCE_KINDS,
};

function keep(item: EvidenceItem, show: string): boolean {
  const trace = item.kind in TRACE_KINDS;
  if (show === 'proof' || show === 'trace') {
    return trace === (show === 'trace');
  }
  return show === 'all' || item.kind === show;
}

/** Whether an item's words hold the searched text (case ignored). */
function says(item: EvidenceItem, text: string): boolean {
  const words = [item.title, item.place, item.description, item.file_name];
  const plain = text.trim().toLowerCase();
  return !plain || words.join(' ').toLowerCase().includes(plain);
}

function Details({ item }: { item: EvidenceItem }) {
  return (
    <>
      {span(item)} — <strong>{EVIDENCE_KINDS[item.kind] ?? item.kind}</strong>
      {item.count > 1 && ` ×${item.count}`} {item.title}
      {item.place && item.place !== item.title && ` · ${item.place}`}
      {item.amount != null && ` · ${item.amount} €`}
      {item.meal_id && ' · repas au Journal'}
      {item.sha256 && (
        <span className="muted"> · SHA-256 {item.sha256.slice(0, 12)}…</span>
      )}
    </>
  );
}

function Item({ item, sel }: { item: EvidenceItem; sel: Selection }) {
  const del = useDeleteEvidence();
  const [open, setOpen] = useState(false);
  const drop = () =>
    window.confirm('Supprimer cette preuve et son fichier ?') &&
    del.mutate(item.id);
  return (
    <li>
      <PickBox sel={sel} id={item.id} /> <Details item={item} />{' '}
      <EvidenceFile id={item.id} name={item.file_name} />
      <button className="btn ghost" onClick={() => setOpen(true)}>
        Détails
      </button>
      <button className="btn ghost" onClick={drop}>
        Supprimer
      </button>
      {open && (
        <EvidenceViewer item={viewable(item)} onClose={() => setOpen(false)} />
      )}
    </li>
  );
}

function Search(props: { value: string; onChange: (v: string) => void }) {
  return (
    <input
      className="input"
      type="search"
      placeholder="Chercher (titre, lieu, détail, fichier)"
      value={props.value}
      onChange={(e) => props.onChange(e.target.value)}
    />
  );
}

function withMeals(items: EvidenceItem[]) {
  const logged = new Set(items.filter((i) => i.meal_id).map((i) => i.id));
  return (ids: string[]) => ids.filter((id) => logged.has(id)).length;
}

function Items(props: { page: EvidenceItem[]; sel: Selection }) {
  return (
    <ul className="care-list">
      {props.page.map((item) => (
        <Item key={item.id} item={item} sel={props.sel} />
      ))}
    </ul>
  );
}

const NOUN = 'preuves et traces (avec leurs fichiers)';

function useShown() {
  const [range, setRange] = useRange(null, 'work.evidence');
  const [show, setShow] = useStored(
    'work.evidence.show',
    'all',
    Object.keys(SHOW),
  );
  const [text, setText] = useStored('work.evidence.text', '');
  const items = useEvidence(range).data ?? [];
  const shown = items.filter((i) => keep(i, show) && says(i, text)).reverse();
  const filters = (
    <>
      <DateRange value={range} onChange={setRange} />
      <Choice options={SHOW} value={show} onChange={setShow} />
      <Search value={text} onChange={setText} />
    </>
  );
  return { items, shown, filters };
}

/** Proofs and traces of a period, newest first, by kind or words. */
export function EvidenceList() {
  const { items, shown, filters } = useShown();
  const sel = useSelection();
  const { page, bar } = usePaging(shown);
  const ids = shown.map((i) => i.id);
  return (
    <>
      <h3>
        Liste : {shown.length} affichée(s) sur {items.length} dans la période
      </h3>
      {filters}
      <BulkBar
        what="evidence"
        noun={NOUN}
        shown={ids}
        sel={sel}
        meals={withMeals(items)}
      />
      {bar}
      <Items page={page} sel={sel} />
    </>
  );
}
