import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import {
  fetchHealthKitStatus,
  type RefusedKind,
  type RefusedLines,
} from '../api/healthkit';
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

/** « 1 relevé », « 1 234 relevés », « 2 lignes refusées ». */
function count(n: number, noun: string): string {
  return `${frNumber(n, 0)} ${n > 1 ? noun.replace(/(\S+)/g, '$1s') : noun}`;
}

/** Each kind refused: type, why, how many, last time (wraps). */
function RefusedList({ kinds }: { kinds: RefusedKind[] }) {
  return (
    <ul className="refused-list">
      {kinds.map((kind) => {
        const last = new Date(kind.last).toLocaleString('fr-FR');
        const lines = `${frNumber(kind.count, 0)} (dernière le ${last})`;
        return (
          <li key={`${kind.type}|${kind.reason}`}>
            <code>{kind.type}</code> — {kind.reason} : {lines}
          </li>
        );
      })}
    </ul>
  );
}

/** The lines the hub refused lately: none, or each type with why. */
function Refused({ refused }: { refused: RefusedLines }) {
  if (refused.checked === 0) {
    return <p className="muted">Lignes refusées : pas encore vérifiable.</p>;
  }
  const checked = count(refused.checked, 'synchro vérifiée');
  const over = `sur ${refused.days} j (${checked})`;
  if (refused.lines === 0) {
    return <p className="muted">✓ Aucune ligne refusée {over}.</p>;
  }
  return (
    <>
      <p className="refused-title">
        ⚠ {count(refused.lines, 'ligne refusée')} {over} :
      </p>
      <RefusedList kinds={refused.kinds} />
    </>
  );
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
    <>
      <p className="muted">
        Dernière synchro : {at} · {count(data.samples, 'relevé')} ·{' '}
        {count(data.workouts, 'entraînement')}
      </p>
      <Refused refused={data.refused} />
    </>
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
