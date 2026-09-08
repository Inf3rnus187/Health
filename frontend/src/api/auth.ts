import { api } from './client';
import type { TokenPair, User } from './types';

export function login(email: string, password: string): Promise<TokenPair> {
  return api<TokenPair>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function refreshTokens(refreshToken: string): Promise<TokenPair> {
  return api<TokenPair>('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function logoutRequest(
  refreshToken: string,
): Promise<{ detail: string }> {
  return api<{ detail: string }>('/auth/logout', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function fetchMe(): Promise<User> {
  return api<User>('/auth/me');
}
