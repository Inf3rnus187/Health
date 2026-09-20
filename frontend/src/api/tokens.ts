import { api } from './client';
import type { ApiToken, TokenCreated } from './types';

export function createToken(
  name: string,
  scopes: string[],
): Promise<TokenCreated> {
  return api<TokenCreated>('/tokens', {
    method: 'POST',
    body: JSON.stringify({ name, scopes }),
  });
}

export function listTokens(): Promise<ApiToken[]> {
  return api<ApiToken[]>('/tokens');
}

export function revokeToken(id: string): Promise<{ detail: string }> {
  return api<{ detail: string }>(`/tokens/${id}`, { method: 'DELETE' });
}
