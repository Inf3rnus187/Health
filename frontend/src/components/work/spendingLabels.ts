import { shortDate } from '../../utils/format';

const MONTHS = [
  'janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin',
  'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.',
]; // prettier-ignore

/** « 02/03 », « sem. du 02/03 », « mars 2026 ». */
export function periodLabel(start: string, bucket: string, long = false) {
  const [year, month, day] = start.split('-');
  if (bucket === 'month') {
    return `${MONTHS[Number(month) - 1]} ${long ? year : year?.slice(2)}`;
  }
  const short = `${day}/${month}`;
  if (bucket === 'week') return long ? `semaine du ${shortDate(start)}` : short;
  return long ? shortDate(start) : short;
}
