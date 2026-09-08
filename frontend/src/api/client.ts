// Thin fetch wrapper: injects the bearer token and normalises errors.
// The access token is held in memory; the refresh token lives in
// localStorage (see AuthProvider).

interface ApiError {
  code: string;
  detail: string;
}

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }
  const res = await fetch(`/api/v1${path}`, { ...init, headers });
  if (!res.ok) {
    throw await toError(res);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

async function toError(res: Response): Promise<Error> {
  const body = (await res.json().catch(() => null)) as ApiError | null;
  return new Error(body?.detail ?? `HTTP ${res.status}`);
}
