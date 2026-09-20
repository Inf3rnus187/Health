import type { Bucket } from '../api/types';

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

/** Format an epoch-ms tick for the current bucket. The 2-digit year is
 *  always shown so a multi-year axis never looks out of order. */
export function formatTick(ms: number, bucket: Bucket): string {
  const date = new Date(ms);
  const day = pad(date.getDate());
  const month = pad(date.getMonth() + 1);
  const year = date.getFullYear();
  if (bucket === 'year') {
    return String(year);
  }
  if (bucket === 'month') {
    return `${month}/${pad(year % 100)}`;
  }
  return `${day}/${month}/${pad(year % 100)}`;
}
