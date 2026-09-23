import type { JournalNight } from '../../api/journalDays';

/** « 6 h 40 » from minutes. */
export function hoursText(minutes: number): string {
  const total = Math.round(minutes);
  return `${Math.floor(total / 60)} h ${String(total % 60).padStart(2, '0')}`;
}

/** « en 1 fois », « en 3 fois » (stretches split by an hour awake). */
export function goesText(night: JournalNight): string {
  return night.blocks ? `en ${night.blocks} fois` : '';
}

/** « 3 réveils », « aucun réveil ». */
export function wakesText(night: JournalNight): string {
  const n = night.awakenings;
  if (n == null) return '';
  if (n === 0) return 'aucun réveil';
  return `${n} réveil${n > 1 ? 's' : ''}`;
}

/** « 23:40 → 06:50 ». */
export function spanText(night: JournalNight): string {
  return night.bedtime && night.wake_time
    ? `${night.bedtime} → ${night.wake_time}`
    : '';
}
