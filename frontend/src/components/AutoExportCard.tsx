import { useState } from 'react';

import type { TokenCreated } from '../api/types';
import { useCreateToken } from '../hooks/useTokens';
import { CopyButton } from './CopyButton';

const ENDPOINT = `${window.location.origin}/api/v1/sync/auto-export`;

function Url({ url }: { url: string }) {
  return (
    <div className="secret">
      <p className="muted">URL Health Auto Export (jeton inclus) :</p>
      <div className="secret-row">
        <code className="secret-code">{url}</code>
        <CopyButton text={url} label="Copier l’URL" />
      </div>
    </div>
  );
}

export function AutoExportCard() {
  const [url, setUrl] = useState<string | null>(null);
  const create = useCreateToken();
  const onCreate = () =>
    create.mutate(undefined, {
      onSuccess: (token: TokenCreated) =>
        setUrl(`${ENDPOINT}?token=${token.token}`),
    });
  return (
    <section className="card">
      <h2>Health Auto Export (JSON)</h2>
      <p className="muted">
        App « Health Auto Export » → Automatisation → REST API : méthode POST,
        format JSON, colle l’URL ci-dessous. Import complet de l’historique ;
        les données arrivent dans Tableaux de bord et Accueil.
      </p>
      <button className="btn" disabled={create.isPending} onClick={onCreate}>
        Créer l’URL Health Auto Export
      </button>
      {url && <Url url={url} />}
    </section>
  );
}
