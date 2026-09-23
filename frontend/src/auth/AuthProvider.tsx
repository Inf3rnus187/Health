import { type ReactNode, useCallback, useEffect, useState } from 'react';

import { fetchMe, login, logoutRequest } from '../api/auth';
import {
  keepTokens,
  onSessionExpired,
  REFRESH_KEY,
  renewSession,
  setAccessToken,
} from '../api/client';
import type { User } from '../api/types';
import { AuthContext } from './context';

/** Renew the 15-minute access token before it runs out (a hidden tab
 * waits: its first call renews it). */
const RENEW_EVERY = 12 * 60 * 1000;

type SetUser = (user: User | null) => void;

async function doSignIn(
  email: string,
  password: string,
  setUser: SetUser,
): Promise<void> {
  keepTokens(await login(email, password));
  setUser(await fetchMe());
}

async function doSignOut(setUser: SetUser): Promise<void> {
  const token = localStorage.getItem(REFRESH_KEY);
  if (token) {
    await logoutRequest(token).catch(() => undefined);
  }
  forget();
  setUser(null);
}

function forget(): void {
  localStorage.removeItem(REFRESH_KEY);
  setAccessToken(null);
}

async function restore(
  setUser: SetUser,
  setReady: (ready: boolean) => void,
): Promise<void> {
  if (localStorage.getItem(REFRESH_KEY)) {
    if (await renewSession()) {
      setUser(await fetchMe().catch(() => null));
    } else {
      forget();
    }
  }
  setReady(true);
}

/** While signed in: renew ahead of time; a lost session: log out. */
function useKeepAlive(user: User | null, expire: () => void): void {
  useEffect(() => {
    onSessionExpired(expire);
    return () => onSessionExpired(null);
  }, [expire]);
  useEffect(() => {
    if (!user) return undefined;
    const renew = () => {
      if (document.visibilityState === 'visible') void renewSession();
    };
    const timer = setInterval(renew, RENEW_EVERY);
    return () => clearInterval(timer);
  }, [user]);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [expired, setExpired] = useState(false);
  const signIn = useCallback(async (email: string, password: string) => {
    await doSignIn(email, password, setUser);
    setExpired(false);
  }, []);
  const signOut = useCallback(() => doSignOut(setUser), []);
  const expire = useCallback(() => {
    forget();
    setExpired(true);
    setUser(null);
  }, []);
  useKeepAlive(user, expire);
  useEffect(() => {
    void restore(setUser, setReady);
  }, []);
  const value = { user, ready, expired, signIn, signOut };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
