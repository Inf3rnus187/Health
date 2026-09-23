import { useState } from 'react';

import type { DayContext, IncompleteDay } from '../../api/workfile';
import { money } from '../../utils/format';
import { EvidenceFile } from '../FileButtons';
import { clockHints } from './dayHints';
import { EvidenceViewer, type Viewable } from './EvidenceViewer';

type Proof = DayContext['evidence'][number];

/** "Preuve présente" or not, at a glance. */
export function ProofBadge({ row }: { row: IncompleteDay }) {
  return row.context.has_proof ? (
    <span className="badge badge-done">preuve présente</span>
  ) : (
    <span className="badge">sans preuve</span>
  );
}

function viewable(p: Proof): Viewable {
  return { ...p, when: p.time, title: p.title || p.label };
}

function detail(p: Proof): string {
  const price = p.amount != null ? `${money(p.amount)} €` : '';
  const place = p.place && p.place !== p.title ? p.place : '';
  return [p.title, place, price].filter(Boolean).join(' · ');
}

function Take(props: { at: string | null; label: string; pick: Pick }) {
  if (!props.at) return null;
  const at = props.at.slice(0, 16);
  return (
    <button className="btn ghost" onClick={() => props.pick(at)}>
      {props.label} {at.slice(11)}
    </button>
  );
}

type Pick = (at: string) => void;

function ProofRow(props: { p: Proof; pick: Pick; view: (p: Proof) => void }) {
  const { p, pick } = props;
  return (
    <tr>
      <td className="nowrap">
        <strong>{p.label}</strong>
      </td>
      <td className="nowrap">{p.time}</td>
      <td>{detail(p)}</td>
      <td className="quick">
        <EvidenceFile id={p.id} name={p.file_name} />
        <button className="btn ghost" onClick={() => props.view(p)}>
          Détails
        </button>
        <Take at={p.at} label="Prendre" pick={pick} />
        <Take at={p.end_at} label="Prendre la fin" pick={pick} />
      </td>
    </tr>
  );
}

/** The day's proofs and traces: look at each one, take its time. */
export function ProofTable(props: { row: IncompleteDay; pick: Pick }) {
  const [shown, setShown] = useState<Proof | null>(null);
  const proofs = props.row.context.evidence;
  if (proofs.length === 0) {
    return <p className="muted">Aucune preuve ni trace ce jour-là.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="data-table">
        <tbody>
          {proofs.map((p) => (
            <ProofRow key={p.id} p={p} pick={props.pick} view={setShown} />
          ))}
        </tbody>
      </table>
      {shown && (
        <EvidenceViewer item={viewable(shown)} onClose={() => setShown(null)} />
      )}
    </div>
  );
}

/** Wake-up, steps and habit: clickable times. */
export function Landmarks(props: { row: IncompleteDay; pick: Pick }) {
  const hints = clockHints(props.row);
  if (hints.length === 0) {
    return <p className="muted">Pas de réveil, de pas ni d’habitude connus.</p>;
  }
  return (
    <div className="chips">
      {hints.map((h) => (
        <button
          key={h.key}
          className="chip"
          title={h.title}
          onClick={() => props.pick(h.at)}
        >
          {h.label}
        </button>
      ))}
    </div>
  );
}
