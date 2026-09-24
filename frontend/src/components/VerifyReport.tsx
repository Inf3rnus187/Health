import { useMutation } from '@tanstack/react-query';
import type { ChangeEvent } from 'react';

import { type Verdict, verifyReport } from '../api/reports';
import { shortDateTime } from '../utils/datetime';

function Answer({ v }: { v: Verdict }) {
  if (!v.authentic || !v.report) {
    return (
      <p className="error">
        ✗ Ce fichier n’est pas un de vos rapports tel que le hub l’a créé (ou il
        a été modifié). Empreinte : {v.sha256.slice(0, 16)}…
      </p>
    );
  }
  return (
    <p>
      ✔ Authentique : rapport créé le {shortDateTime(v.report.created_at)},
      identique octet pour octet (SHA-256 {v.sha256.slice(0, 16)}…).
    </p>
  );
}

/** Check that a copy of a report is exactly the one the hub made. */
export function VerifyReport() {
  const check = useMutation({ mutationFn: verifyReport });
  const pick = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) check.mutate(file);
    event.target.value = '';
  };
  return (
    <div className="photo-pick">
      <label className="btn ghost">
        🔏 Vérifier un fichier
        <input type="file" hidden onChange={pick} />
      </label>
      {check.isPending && <p className="muted">Vérification…</p>}
      {check.data && <Answer v={check.data} />}
      {check.isError && <p className="error">{check.error.message}</p>}
    </div>
  );
}
