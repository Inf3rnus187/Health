import { useState } from 'react';

import { useCreateToken, useRevokeToken, useTokens } from '../hooks/useTokens';
import { CopyButton } from './CopyButton';
import { ShortcutRecipe } from './ShortcutRecipe';
import { TokenList } from './TokenList';

const ENDPOINT = `${window.location.origin}/api/v1/imports/apple-health`;

export function MobileSyncCard() {
  const [secret, setSecret] = useState<string | null>(null);
  const tokens = useTokens().data ?? [];
  const create = useCreateToken();
  const revoke = useRevokeToken();
  const onCreate = () =>
    create.mutate(undefined, { onSuccess: (t) => setSecret(t.token) });
  return (
    <section className="card">
      <h2>Synchro iPhone (export CSV)</h2>
      <p className="muted">
        iOS bloque l’import d’un raccourci non signé. La voie fiable : le
        raccourci « SimpleHealthExportCSV » exporte tout Santé en CSV et les
        envoie ici. Crée un jeton, puis colle-le + l’URL dans son envoi.
      </p>
      <button className="btn" disabled={create.isPending} onClick={onCreate}>
        Créer un jeton d’upload
      </button>
      {secret && <Secret secret={secret} />}
      <ShortcutRecipe endpoint={ENDPOINT} />
      <TokenList tokens={tokens} onRevoke={(id) => revoke.mutate(id)} />
    </section>
  );
}

function Secret({ secret }: { secret: string }) {
  return (
    <div className="secret">
      <p className="muted">Jeton (affiché une seule fois) :</p>
      <div className="secret-row">
        <code className="secret-code">{secret}</code>
        <CopyButton text={secret} label="Copier le jeton" />
      </div>
    </div>
  );
}
