import type { FormEvent } from 'react';

import { Field } from './Field';

interface LoginFormProps {
  email: string;
  password: string;
  error: string;
  onEmail: (value: string) => void;
  onPassword: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
}

export function LoginForm(props: LoginFormProps) {
  return (
    <form className="login-card" onSubmit={props.onSubmit}>
      <h1>Phoenix Health Hub</h1>
      <Field
        id="email"
        label="Email"
        type="email"
        value={props.email}
        onChange={props.onEmail}
      />
      <Field
        id="password"
        label="Mot de passe"
        type="password"
        value={props.password}
        onChange={props.onPassword}
      />
      {props.error ? <p className="error">{props.error}</p> : null}
      <button className="btn" type="submit">
        Se connecter
      </button>
    </form>
  );
}
