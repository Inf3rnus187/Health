// Thin fetch wrapper: injects the bearer token and normalises errors.
// The access token (15 min) is held in memory; the refresh token (14
// days) lives in localStorage. An expired access token is renewed with
// the refresh token and the call replayed — once, for every call waiting
// at the same time — so a page left open never ends on « 401 ». A hub
// that does not answer (restarting after an update: 502) never logs
// out: only a refused refresh token does.

interface ApiError {
  code: string;
  detail: string;
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

/** Where the refresh token is kept (shared by the tabs). */
export const REFRESH_KEY = 'phoenix.refresh';

let accessToken: string | null = null;
let renewing: Promise<Renewal> | null = null;
let onExpired: (() => void) | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

/** Called when the session cannot be renewed (back to the login page). */
export function onSessionExpired(handler: (() => void) | null): void {
  onExpired = handler;
}

/** Store a new pair (after login or renewal). */
export function keepTokens(pair: TokenPair): void {
  accessToken = pair.access_token;
  localStorage.setItem(REFRESH_KEY, pair.refresh_token);
}

/** How a renewal ended: a new pair, a refused token (log out), or a hub
 * that did not answer (keep the session, try again). */
export type Renewal = 'renewed' | 'refused' | 'unreachable';

/** Longest wait for the hub's answer before calling it unreachable. */
const REFRESH_TIMEOUT = 15_000;

async function refreshWith(
  token: string,
): Promise<TokenPair | 'refused' | 'unreachable'> {
  const res = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: token }),
    signal: AbortSignal.timeout(REFRESH_TIMEOUT),
  }).catch(() => null);
  if (!res || res.status >= 500) return 'unreachable';
  return res.ok ? ((await res.json()) as TokenPair) : 'refused';
}

const pause = (ms: number) => new Promise((done) => setTimeout(done, ms));

/** Renew with the stored refresh token; another tab may have just done
 * it (the token then changed in localStorage): use the new one. */
async function renew(): Promise<Renewal> {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const token = localStorage.getItem(REFRESH_KEY);
    if (!token) return 'refused';
    const got = await refreshWith(token);
    if (typeof got === 'object') {
      keepTokens(got);
      return 'renewed';
    }
    if (got === 'unreachable') return got;
    await pause(400);
    if (localStorage.getItem(REFRESH_KEY) === token) return 'refused';
  }
  return 'refused';
}

/** Renew the session once, whoever asks at the same time. */
export function renewSession(): Promise<Renewal> {
  renewing ??= renew().finally(() => {
    renewing = null;
  });
  return renewing;
}

function withToken(init: RequestInit): RequestInit {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  return { ...init, headers };
}

/** ``fetch`` of an ``/api/v1`` path with the session: an expired token
 * is renewed and the call replayed; no renewal possible: logged out. */
export async function authFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const res = await fetch(`/api/v1${path}`, withToken(init));
  if (res.status !== 401 || path.startsWith('/auth/')) return res;
  const renewal = await renewSession();
  if (renewal === 'renewed') return fetch(`/api/v1${path}`, withToken(init));
  if (renewal === 'refused') onExpired?.();
  return res;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  const res = await authFetch(path, { ...init, headers });
  if (!res.ok) {
    throw await toError(res);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

/** An error with the API's message (« Erreur 500 » when it has none). */
export async function toError(res: Response): Promise<Error> {
  const body = (await res.json().catch(() => null)) as ApiError | null;
  return new Error(body?.detail ?? `Erreur ${res.status}`);
}
