/** Hours as ``8 h 49``. */
export function hm(hours: number | null | undefined): string {
  if (hours === null || hours === undefined) {
    return '—';
  }
  const minutes = Math.round(hours * 60);
  const rest = String(minutes % 60).padStart(2, '0');
  return `${Math.floor(minutes / 60)} h ${rest}`;
}

/** ``HH:MM`` of an ISO instant (browser local time). */
export function clockTime(iso: string | null): string {
  if (!iso) {
    return '—';
  }
  return new Date(iso).toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

const CONTRACT_KEY = 'work-contract-hours';

/** The weekly contract hours remembered in this browser (35 by default). */
export function storedContract(): number {
  try {
    const value = Number(localStorage.getItem(CONTRACT_KEY));
    return value > 0 ? value : 35;
  } catch {
    return 35;
  }
}

export function rememberContract(hours: number): void {
  try {
    localStorage.setItem(CONTRACT_KEY, String(hours));
  } catch {
    // private window: not remembered
  }
}
