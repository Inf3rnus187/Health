import { authFetch } from './client';

/** Types for files served as "application/octet-stream". */
const TYPES: Record<string, string> = {
  pdf: 'application/pdf',
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  gif: 'image/gif',
  webp: 'image/webp',
  heic: 'image/heic',
  txt: 'text/plain',
  csv: 'text/plain',
  json: 'application/json',
};

/** A private file (``/api/v1`` path) as a blob the browser can show. */
async function blobOf(path: string, name: string): Promise<Blob> {
  const res = await authFetch(path);
  if (!res.ok) throw new Error(`Erreur ${res.status}`);
  const blob = await res.blob();
  const guessed = TYPES[name.split('.').pop()?.toLowerCase() ?? ''];
  const shown = !blob.type || blob.type === 'application/octet-stream';
  return shown && guessed ? new Blob([blob], { type: guessed }) : blob;
}

/** Open a private file in a new tab (as a blob, never a download).
 *
 * The tab opens at the click, so no popup blocker stops it; the file is
 * loaded in it once fetched. */
export async function openFile(path: string, name = ''): Promise<void> {
  const tab = window.open('', '_blank');
  try {
    const url = URL.createObjectURL(await blobOf(path, name));
    if (tab) tab.location.href = url;
    else window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (error) {
    tab?.close();
    throw error;
  }
}
