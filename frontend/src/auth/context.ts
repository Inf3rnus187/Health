import { createContext } from 'react';

import type { User } from '../api/types';

export interface AuthValue {
  user: User | null;
  ready: boolean;
  /** The session ran out (the login page says so). */
  expired: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthValue | null>(null);
