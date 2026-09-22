import { useState } from 'react';

import type { TimelineItem } from '../../api/record';
import { useRecord } from '../../hooks/useRecord';
import { KIND_LABELS } from '../../medical/kinds';
import { shortDate } from '../../utils/format';

const TYPE_LABEL: Record<TimelineItem['type'], string> = {
  document: 'Document',
  condition: 'Diagnostic',
  treatment_start: 'Début de traitement',
  treatment_stop: 'Arrêt de traitement',
  appointment: 'Rendez-vous',
};
const STEP = 15;

function badge(item: TimelineItem): string {
  if (item.type === 'document' && item.kind) {
    return KIND_LABELS[item.kind] ?? item.kind;
  }
  return TYPE_LABEL[item.type];
}

function Row({ item }: { item: TimelineItem }) {
  return (
    <li className="timeline-item">
      <span className="timeline-date">{shortDate(item.date)}</span>
      <span className="badge">{badge(item)}</span>
      <span className="import-name">{item.title}</span>
      {item.detail && <p className="muted timeline-detail">{item.detail}</p>}
    </li>
  );
}

/** Documents, diagnoses, treatments and appointments on one timeline. */
export function TimelineCard() {
  const [shown, setShown] = useState(STEP);
  const items = useRecord().data?.timeline ?? [];
  if (items.length === 0) {
    return null;
  }
  return (
    <section className="card">
      <h2>Chronologie</h2>
      <ul className="timeline">
        {items.slice(0, shown).map((item) => (
          <Row key={`${item.type}-${item.id}-${item.date}`} item={item} />
        ))}
      </ul>
      {items.length > shown && (
        <button className="btn ghost" onClick={() => setShown(shown + STEP)}>
          Voir plus
        </button>
      )}
    </section>
  );
}
