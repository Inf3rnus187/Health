import { useState } from 'react';

import type { TokenCreated } from '../api/types';
import { useCreateToken } from '../hooks/useTokens';
import { CopyButton } from './CopyButton';
import { ShortcutRecipe } from './ShortcutRecipe';

const ENDPOINT = `${window.location.origin}/api/v1/imports/apple-health`;

export function MobileSyncCard() {
  const [url, setUrl] = useState<string | null>(null);
  const create = useCreateToken();
  const save = (t: TokenCreated) => setUrl(`${ENDPOINT}?token=${t.token}`);
  const onCreate = () => create.mutate(undefined, { onSuccess: save });
  return (
    <section className="card">
      <h2>Synchro iPhone (export CSV)</h2>
      <p className="muted">
        iOS bloque les raccourcis non signés. Voie fiable : le raccourci «
        SimpleHealthExportCSV » exporte tout Santé en CSV et l’envoie ici. Crée
        l’URL (jeton inclus), colle-la dans son envoi — aucun en-tête.
      </p>
      <button className="btn" disabled={create.isPending} onClick={onCreate}>
        Créer l’URL d’upload
      </button>
      {url && <UploadUrl url={url} />}
      <ShortcutRecipe />
    </section>
  );
}

function UploadUrl({ url }: { url: string }) {
  return (
    <div className="secret">
      <p className="muted">URL d’upload (jeton inclus, affichée une fois) :</p>
      <div className="secret-row">
        <code className="secret-code">{url}</code>
        <CopyButton text={url} label="Copier l’URL" />
      </div>
    </div>
  );
}
