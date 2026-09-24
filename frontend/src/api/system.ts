import { api } from './client';

/** What ./update.sh (on the Docker host) says about updates. */
export interface UpdateState {
  /** False: ./update.sh never ran on the host. */
  known: boolean;
  /** Changes waiting on GitHub. */
  behind: number;
  commits: string[];
  /** Parts to rebuild (« interface web », « API et worker »…). */
  rebuild: string[];
  checked_at: string | null;
  current: string | null;
  latest: string | null;
  /** The host's cron is active: « Installer » works. */
  watcher: boolean;
  /** idle, requested, running, done or failed. */
  state: string;
  /** When the request was made, or the last update changed state. */
  since: string | null;
  /** A request nobody takes, or an update that never ends. */
  stalled: boolean;
  message: string;
  command: string;
}

export const fetchUpdate = () => api<UpdateState>('/system/update');
export const requestUpdate = () =>
  api<UpdateState>('/system/update', { method: 'POST' });

/** The build installed on the server (null: unknown, e.g. in dev). */
export async function installedBuild(): Promise<string | null> {
  const res = await fetch('/version.json', { cache: 'no-store' }).catch(
    () => null,
  );
  if (!res?.ok) return null;
  const body = (await res.json().catch(() => null)) as {
    build?: string;
  } | null;
  return body?.build ?? null;
}
