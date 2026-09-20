import { useState } from 'react';

import { useCreateToken, useRevokeToken, useTokens } from '../hooks/useTokens';
import { ShortcutRecipe } from './ShortcutRecipe';
import { TokenList } from './TokenList';
import { TokenSecret } from './TokenSecret';

const ENDPOINT = `${window.location.origin}/api/v1/ingest/watch`;

export function MobileSyncCard() {
  const [secret, setSecret] = useState<string | null>(null);
  const tokens = useTokens().data ?? [];
  const create = useCreateToken();
  const revoke = useRevokeToken();
  const onCreate = () =>
    create.mutate(undefined, { onSuccess: (token) => setSecret(token.token) });
  return (
    <section className="card">
      <h2>Synchro iPhone (Raccourci)</h2>
      <p className="muted">
        Sans app à installer : un Raccourci lit tes données Santé et les envoie
        ici (métriques du jour). L’upload du zip reste nécessaire pour
        l’historique complet, les ECG et le CDA.
      </p>
      <button className="btn" disabled={create.isPending} onClick={onCreate}>
        Créer un jeton de synchro
      </button>
      {secret && <TokenSecret secret={secret} />}
      <ShortcutRecipe endpoint={ENDPOINT} />
      <TokenList tokens={tokens} onRevoke={(id) => revoke.mutate(id)} />
    </section>
  );
}
