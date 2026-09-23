/** Render an ISO timestamp as ``dd/MM/yyyy HH:mm`` (empty if missing). */
export function shortDateTime(iso: string | null): string {
  if (!iso) {
    return '—';
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso.slice(0, 16).replace('T', ' ');
  }
  const pad = (value: number) => String(value).padStart(2, '0');
  const day = `${pad(date.getDate())}/${pad(date.getMonth() + 1)}`;
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`;
  return `${day}/${date.getFullYear()} ${time}`;
}

/** An instant as a local ``YYYY-MM-DDTHH:MM`` (datetime-local value). */
export function localStamp(iso: string): string {
  const at = new Date(iso);
  at.setMinutes(at.getMinutes() - at.getTimezoneOffset());
  return at.toISOString().slice(0, 16);
}
