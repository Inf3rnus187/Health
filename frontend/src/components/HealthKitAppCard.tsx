import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { fetchHealthKitStatus } from '../api/healthkit';
import type { TokenCreated } from '../api/types';
import { useMintToken } from '../hooks/useTokens';
import { frNumber } from '../utils/format';
import { CopyButton } from './CopyButton';

const ENDPOINT = `${window.location.origin}/api/v1/sync/healthkit`;

function Secret({ token }: { token: string }) {
  return (
    <div className="secret">
      <p className="muted">
        Jeton de l’app (affiché une seule fois), à envoyer dans l’en-tête «
        Authorization: Bearer … » :
      </p>
      <div className="secret-row">
        <code className="secret-code">{token}</code>
        <CopyButton text={token} label="Copier le jeton" />
      </div>
    </div>
  );
}

/** « 1 relevé », « 1 234 relevés ». */
function count(n: number, noun: string): string {
  return `${frNumber(n, 0)} ${noun}${n > 1 ? 's' : ''}`;
}

function LastSync() {
  const { data } = useQuery({
    queryKey: ['healthkit-sync'],
    queryFn: fetchHealthKitStatus,
  });
  if (!data) return null;
  if (!data.last_sync_at) {
    return <p className="muted">Aucune synchro reçue pour l’instant.</p>;
  }
  const at = new Date(data.last_sync_at).toLocaleString('fr-FR');
  return (
    <p className="muted">
      Dernière synchro : {at} · {count(data.samples, 'relevé')} ·{' '}
      {count(data.workouts, 'entraînement')}
    </p>
  );
}

/** Where the app sends, with a copy button (wraps on a phone). */
function Address() {
  return (
    <>
      <p className="muted">
        Ton app envoie ce que HealthKit contient (relevés, sommes, sommeil,
        entraînements, suppressions) en POST JSON à cette adresse (format :
        guide « Ingestion ») :
      </p>
      <div className="secret-row">
        <code className="secret-code">{ENDPOINT}</code>
        <CopyButton text={ENDPOINT} label="Copier l’adresse" />
      </div>
    </>
  );
}

/** The iPhone app that sends HealthKit to the hub: address and token. */
export function HealthKitAppCard() {
  const [token, setToken] = useState<string | null>(null);
  const mint = useMintToken();
  const onCreate = () =>
    mint.mutate(
      { name: 'App iPhone (HealthKit)', scopes: ['write:measurements'] },
      { onSuccess: (made: TokenCreated) => setToken(made.token) },
    );
  return (
    <section className="card">
      <h2>App iPhone (HealthKit)</h2>
      <Address />
      <LastSync />
      <button className="btn" disabled={mint.isPending} onClick={onCreate}>
        Créer un jeton pour l’app
      </button>
      {token && <Secret token={token} />}
    </section>
  );
}
