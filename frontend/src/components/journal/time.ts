/** ``HH:MM`` of an ISO instant, in the browser's local time. */
export function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Now as a ``datetime-local`` value (``YYYY-MM-DDTHH:MM``). */
export function nowLocal(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

/** An ISO instant as a ``datetime-local`` value, in local time. */
export function localInput(iso: string): string {
  const at = new Date(iso);
  at.setMinutes(at.getMinutes() - at.getTimezoneOffset());
  return at.toISOString().slice(0, 16);
}

/** The usual meal for the current hour. */
export function mealOfNow(): string {
  const hour = new Date().getHours() + new Date().getMinutes() / 60;
  if (hour < 10.5) return 'breakfast';
  if (hour < 15) return 'lunch';
  if (hour < 18) return 'snack';
  return 'dinner';
}
