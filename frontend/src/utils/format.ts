// French display helpers: decimal comma, signed deltas, dd/MM/yyyy dates.

export function frNumber(value: number, digits = 1): string {
  return value.toLocaleString('fr-FR', { maximumFractionDigits: digits });
}

/** An amount with two decimals: ``38,40``. */
export function money(value: number): string {
  return value.toLocaleString('fr-FR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Signed value with a true minus sign; "0" stays unsigned. */
export function signed(value: number, digits = 1): string {
  const abs = frNumber(Math.abs(value), digits);
  if (Number(abs.replace(',', '.')) === 0) {
    return abs;
  }
  return `${value < 0 ? '−' : '+'}${abs}`;
}

/** Render a ``YYYY-MM-DD`` date key as ``dd/MM/yyyy`` (— if missing). */
export function shortDate(dateKey: string | null | undefined): string {
  if (!dateKey) {
    return '—';
  }
  const [year, month, day] = dateKey.slice(0, 10).split('-');
  return year && month && day ? `${day}/${month}/${year}` : dateKey;
}

/** Today's date key in the browser's local time zone. */
export function localToday(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 10);
}
