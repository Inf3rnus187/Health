// Thin fetch wrapper: injects the bearer token and normalises errors.
// The access token (15 min) is held in memory; the refresh token (14
// days) lives in localStorage. An expired access token is renewed with
// the refresh token and the call replayed — once, for every call waiting
// at the same time — so a page left open never ends on « 401 ».

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
let renewing: Promise<boolean> | null = null;
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

async function refreshWith(token: string): Promise<TokenPair | null> {
  const res = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: token }),
  }).catch(() => null);
  return res?.ok ? ((await res.json()) as TokenPair) : null;
}

const pause = (ms: number) => new Promise((done) => setTimeout(done, ms));

/** Renew with the stored refresh token; another tab may have just done
 * it (the token then changed in localStorage): use the new one. */
async function renew(): Promise<boolean> {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const token = localStorage.getItem(REFRESH_KEY);
    if (!token) return false;
    const pair = await refreshWith(token);
    if (pair) {
      keepTokens(pair);
      return true;
    }
    await pause(400);
    if (localStorage.getItem(REFRESH_KEY) === token) return false;
  }
  return false;
}

/** Renew the session once, whoever asks at the same time. */
export function renewSession(): Promise<boolean> {
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
  if (await renewSession()) return fetch(`/api/v1${path}`, withToken(init));
  onExpired?.();
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
