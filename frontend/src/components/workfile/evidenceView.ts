import { EVIDENCE_KINDS, type EvidenceItem } from '../../api/workfile';
import type { Viewable } from './EvidenceViewer';

function fmt(iso: string, withTime: boolean): string {
  const at = new Date(iso);
  return withTime
    ? at.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
    : at.toLocaleDateString('fr-FR');
}

/** When an item happened: « 07/05/2026 23:52 → 08/05/2026 00:20 ». */
export function span(item: EvidenceItem): string {
  const end = item.ended_at ? ` → ${fmt(item.ended_at, true)}` : '';
  return `${fmt(item.occurred_at, item.time_known)}${end}`;
}

/** A stored item as the viewer shows it. */
export function viewable(item: EvidenceItem): Viewable {
  const label = EVIDENCE_KINDS[item.kind] ?? item.kind;
  return { ...item, label, when: span(item), title: item.title || label };
}
