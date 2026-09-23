import { useState } from 'react';

import {
  EVIDENCE_KINDS,
  type EvidenceItem,
  TRACE_KINDS,
} from '../../api/workfile';
import { useDeleteEvidence, useEvidence } from '../../hooks/useWorkFile';
import { useRange } from '../../utils/range';
import { DateRange } from '../DateRange';
import { usePaging } from '../Paging';
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

function Item({ item }: { item: EvidenceItem }) {
  const del = useDeleteEvidence();
  const [open, setOpen] = useState(false);
  const drop = () =>
    window.confirm('Supprimer cette preuve et son fichier ?') &&
    del.mutate(item.id);
  return (
    <li>
      <Details item={item} />{' '}
      <button className="btn ghost" onClick={() => setOpen(true)}>
        Voir
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

/** Proofs and traces of a period, newest first, by kind, page by page. */
export function EvidenceList() {
  const [range, setRange] = useRange(null);
  const [show, setShow] = useState('all');
  const items = useEvidence(range).data ?? [];
  const shown = items.filter((i) => keep(i, show)).reverse();
  const { page, bar } = usePaging(shown);
  return (
    <>
      <h3>
        Liste : {shown.length} affichée(s) sur {items.length} dans la période
      </h3>
      <DateRange value={range} onChange={setRange} />
      <Choice options={SHOW} value={show} onChange={setShow} />
      {bar}
      <ul className="care-list">
        {page.map((item) => (
          <Item key={item.id} item={item} />
        ))}
      </ul>
    </>
  );
}
