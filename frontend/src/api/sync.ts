import { downloadRecord } from './records';

// Download the pre-filled iPhone Shortcut. The public origin is passed so
// the file's embedded endpoint points back at this server (reachable from
// the phone on the same network / domain).
export function downloadShortcut(): Promise<void> {
  const base = encodeURIComponent(window.location.origin);
  return downloadRecord(
    `/sync/shortcut?base=${base}`,
    'Phoenix Sante.shortcut',
  );
}
