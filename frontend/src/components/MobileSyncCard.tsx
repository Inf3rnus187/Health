import { useState } from 'react';

import { downloadShortcut } from '../api/sync';
import { useRevokeToken, useTokens } from '../hooks/useTokens';
import { ShortcutRecipe } from './ShortcutRecipe';
import { TokenList } from './TokenList';

export function MobileSyncCard() {
  const tokens = useTokens().data ?? [];
  const revoke = useRevokeToken();
  return (
    <section className="card">
      <h2>Synchro iPhone (Raccourci)</h2>
      <p className="muted">
        Télécharge un raccourci prêt à l’emploi : le jeton et l’adresse de ton
        serveur sont déjà inclus. Un tap pour envoyer ton poids du jour, rien à
        configurer, aucun JSON à modifier.
      </p>
      <DownloadShortcut />
      <ShortcutRecipe />
      <TokenList tokens={tokens} onRevoke={(id) => revoke.mutate(id)} />
    </section>
  );
}

function DownloadShortcut() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const onClick = async () => {
    setBusy(true);
    setError(null);
    try {
      await downloadShortcut();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Échec du téléchargement');
    } finally {
      setBusy(false);
    }
  };
  return (
    <div>
      <button className="btn" disabled={busy} onClick={() => void onClick()}>
        {busy ? 'Préparation…' : 'Télécharger le Raccourci (pré-rempli)'}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
