import { useState } from 'react';

import { EVIDENCE_KINDS, type EvidenceItem } from '../../api/workfile';
import { useEvidence } from '../../hooks/useWorkFile';
import { localStamp } from '../../utils/datetime';
import { EvidenceViewer } from './EvidenceViewer';
import { span, viewable } from './evidenceView';

type Field = 'start' | 'end';

function nextDay(day: string): string {
  const [y, m, d] = day.split('-').map(Number);
  const at = new Date(Date.UTC(y ?? 0, (m ?? 1) - 1, (d ?? 1) + 1));
  return at.toISOString().slice(0, 10);
}

type Pick = (field: Field, at: string) => void;

function Take(props: { item: EvidenceItem; pick: Pick }) {
  if (!props.item.time_known) return null;
  const at = localStamp(props.item.occurred_at);
  return (
    <>
      <button className="btn ghost" onClick={() => props.pick('start', at)}>
        → embauche
      </button>
      <button className="btn ghost" onClick={() => props.pick('end', at)}>
        → débauche
      </button>
    </>
  );
}

function Line(props: { item: EvidenceItem; view: () => void; pick: Pick }) {
  const { item } = props;
  const kind = EVIDENCE_KINDS[item.kind] ?? item.kind;
  return (
    <li>
      <strong>{kind}</strong> {span(item)} {item.title}{' '}
      <button className="btn ghost" onClick={props.view}>
        Voir
      </button>
      <Take item={item} pick={props.pick} />
    </li>
  );
}

/** The proofs and traces of a day and of the morning after it. */
export function DayProofs(props: { day: string; pick: Pick }) {
  const range = { start: props.day, end: nextDay(props.day) };
  const items = useEvidence(range).data ?? [];
  const [shown, setShown] = useState<EvidenceItem | null>(null);
  if (items.length === 0) return <p className="muted">Aucune preuve.</p>;
  return (
    <ul className="care-list">
      {items.map((item) => (
        <Line
          key={item.id}
          item={item}
          view={() => setShown(item)}
          pick={props.pick}
        />
      ))}
      {shown && (
        <EvidenceViewer item={viewable(shown)} onClose={() => setShown(null)} />
      )}
    </ul>
  );
}
