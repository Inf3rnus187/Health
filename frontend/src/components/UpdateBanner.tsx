import { useState } from 'react';

import type { UpdateState } from '../api/system';
import {
  useNewBuild,
  useRequestUpdate,
  useUpdateState,
} from '../hooks/useUpdates';
import { readStored, writeStored } from '../utils/stored';
import { CopyButton } from './CopyButton';

function Reload() {
  return (
    <div className="update-banner">
      <span>Nouvelle version installée.</span>
      <button className="btn" onClick={() => window.location.reload()}>
        Recharger
      </button>
    </div>
  );
}

function what(u: UpdateState): string {
  const count = `${u.behind} changement${u.behind > 1 ? 's' : ''}`;
  const parts = u.rebuild.length
    ? `à reconstruire sur l’hôte : ${u.rebuild.join(', ')}`
    : 'rien à reconstruire (documentation seulement)';
  return `Mise à jour disponible : ${count} — ${parts}.`;
}

function Install({ u }: { u: UpdateState }) {
  const ask = useRequestUpdate();
  if (!u.watcher) {
    return (
      <span className="muted">
        Sur l’hôte, dans le dossier du hub : <code>{u.command}</code>{' '}
        <CopyButton text={u.command} /> (ou{' '}
        <code>{u.command} --install-cron</code> une fois, pour ce bouton).
      </span>
    );
  }
  return (
    <>
      <button className="btn" onClick={() => ask.mutate()}>
        Installer
      </button>
      {ask.error && <span className="error">{ask.error.message}</span>}
    </>
  );
}

function Available(props: { u: UpdateState; later: () => void }) {
  const { u } = props;
  return (
    <div className="update-banner">
      <span>{what(u)}</span>
      <Install u={u} />
      <button className="btn ghost" onClick={props.later}>
        Plus tard
      </button>
      <details>
        <summary>Voir les changements</summary>
        <ul className="care-list">
          {u.commits.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </details>
    </div>
  );
}

function Running({ u }: { u: UpdateState }) {
  const failed = u.state === 'failed';
  return (
    <div className={failed ? 'update-banner failed' : 'update-banner'}>
      {failed
        ? `La mise à jour a échoué : ${u.message}`
        : 'Mise à jour en cours sur l’hôte (1 à 5 min). La page proposera ' +
          'de recharger une fois la nouvelle version installée.'}
    </div>
  );
}

/** A new build installed, an update waiting on GitHub, or one running. */
export function UpdateBanner() {
  const newer = useNewBuild();
  const u = useUpdateState().data;
  const [later, setLater] = useState(readStored<string>('update.later'));
  if (newer) return <Reload />;
  if (!u) return null;
  if (['requested', 'running', 'failed'].includes(u.state)) {
    return <Running u={u} />;
  }
  if (u.behind === 0 || later === u.latest) return null;
  const postpone = () => {
    writeStored('update.later', u.latest);
    setLater(u.latest);
  };
  return <Available u={u} later={postpone} />;
}
