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
import { hub, ms } from '../settings';
import { AuthContext } from './context';

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

const pause = (ms: number) => new Promise((done) => setTimeout(done, ms));

/** Back into the session kept in this browser. A hub that does not
 * answer (restarting after an update) is waited for, never a logout;
 * only a refused session goes back to the login page. */
async function restore(
  setUser: SetUser,
  setWaiting: (waiting: boolean) => void,
): Promise<void> {
  while (localStorage.getItem(REFRESH_KEY)) {
    const renewal = await renewSession();
    if (renewal === 'refused') {
      forget();
      return;
    }
    const me = renewal === 'renewed' ? await fetchMe().catch(() => null) : null;
    if (me) {
      setUser(me);
      return;
    }
    setWaiting(true);
    await pause(ms(hub().retry_s));
  }
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
    // Renewed before the access token runs out (a hidden tab waits:
    // its first call renews it).
    const timer = setInterval(renew, ms(hub().renew_every_s));
    return () => clearInterval(timer);
  }, [user]);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [waiting, setWaiting] = useState(false);
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
    void restore(setUser, setWaiting).finally(() => setReady(true));
  }, []);
  const value = { user, ready, waiting, expired, signIn, signOut };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
