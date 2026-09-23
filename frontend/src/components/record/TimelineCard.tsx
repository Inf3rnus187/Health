import type { TimelineItem } from '../../api/record';
import { useRecord } from '../../hooks/useRecord';
import { KIND_LABELS } from '../../medical/kinds';
import { shortDate } from '../../utils/format';
import { useStored } from '../../utils/stored';
import { usePaging } from '../Paging';
import { Choice } from '../workfile/fields';

const TYPE_LABEL: Record<TimelineItem['type'], string> = {
  document: 'Document',
  condition: 'Diagnostic',
  treatment_start: 'Début de traitement',
  treatment_stop: 'Arrêt de traitement',
  appointment: 'Rendez-vous',
};
/** What the timeline shows (an imported agenda can drown the rest). */
const SHOW: Record<string, string> = {
  all: 'Tout',
  document: 'Documents',
  condition: 'Diagnostics',
  treatment: 'Traitements',
  appointment: 'Rendez-vous',
  medical: 'Tout sauf les rendez-vous',
};

function keep(item: TimelineItem, show: string): boolean {
  if (show === 'all') return true;
  if (show === 'medical') return item.type !== 'appointment';
  return item.type.startsWith(show);
}

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

function Items({ items }: { items: TimelineItem[] }) {
  const { page, bar } = usePaging(items, 25);
  return (
    <>
      {bar}
      <ul className="timeline">
        {page.map((item) => (
          <Row key={`${item.type}-${item.id}-${item.date}`} item={item} />
        ))}
      </ul>
    </>
  );
}

/** Documents, diagnoses, treatments and appointments on one timeline. */
export function TimelineCard() {
  const items = useRecord().data?.timeline ?? [];
  const [show, setShow] = useStored(
    'record.timeline',
    'all',
    Object.keys(SHOW),
  );
  if (items.length === 0) {
    return null;
  }
  const kept = items.filter((item) => keep(item, show));
  return (
    <section className="card">
      <h2>Chronologie ({kept.length})</h2>
      <div className="toolbar">
        <Choice options={SHOW} value={show} onChange={setShow} />
      </div>
      <Items items={kept} />
    </section>
  );
}
