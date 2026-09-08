import { type ReactNode, useCallback, useEffect, useState } from 'react';

import { fetchMe, login, logoutRequest, refreshTokens } from '../api/auth';
import { setAccessToken } from '../api/client';
import type { User } from '../api/types';
import { AuthContext } from './context';

const STORAGE_KEY = 'phoenix.refresh';

type SetUser = (user: User | null) => void;

async function doSignIn(
  email: string,
  password: string,
  setUser: SetUser,
): Promise<void> {
  const pair = await login(email, password);
  setAccessToken(pair.access_token);
  localStorage.setItem(STORAGE_KEY, pair.refresh_token);
  setUser(await fetchMe());
}

async function doSignOut(setUser: SetUser): Promise<void> {
  const token = localStorage.getItem(STORAGE_KEY);
  if (token) {
    await logoutRequest(token).catch(() => undefined);
  }
  localStorage.removeItem(STORAGE_KEY);
  setAccessToken(null);
  setUser(null);
}

async function restore(
  setUser: SetUser,
  setReady: (ready: boolean) => void,
): Promise<void> {
  const token = localStorage.getItem(STORAGE_KEY);
  if (token) {
    try {
      const pair = await refreshTokens(token);
      setAccessToken(pair.access_token);
      localStorage.setItem(STORAGE_KEY, pair.refresh_token);
      setUser(await fetchMe());
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }
  setReady(true);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const signIn = useCallback(
    (email: string, password: string) => doSignIn(email, password, setUser),
    [],
  );
  const signOut = useCallback(() => doSignOut(setUser), []);
  useEffect(() => {
    void restore(setUser, setReady);
  }, []);
  const value = { user, ready, signIn, signOut };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
