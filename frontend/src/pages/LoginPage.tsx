import { type FormEvent, useState } from 'react';

import { LoginForm } from '../components/LoginForm';
import { useAuth } from '../auth/useAuth';

export function LoginPage() {
  const { signIn, expired } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(
    expired ? 'Session expirée : reconnecte-toi.' : '',
  );
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setError('');
    signIn(email, password).catch(() => setError('Identifiants invalides.'));
  };
  return (
    <LoginForm
      email={email}
      password={password}
      error={error}
      onEmail={setEmail}
      onPassword={setPassword}
      onSubmit={submit}
    />
  );
}
