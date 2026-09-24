import { useState } from 'react';

import type { UpdateState } from '../api/system';
import { useAuth } from '../auth/useAuth';
import {
  useNewBuild,
  useRequestUpdate,
  useUpdateState,
} from '../hooks/useUpdates';
import { readStored, writeStored } from '../utils/stored';
import { CopyButton } from './CopyButton';

/** An update done this recently is confirmed (« ✓ … installée »). */
const RECENT_MS = 30 * 60 * 1000;
const LOG = 'tail -50 run/update.log';

/** « 01:12 » today, « 23/09 01:12 » another day. */
function hour(iso: string | null): string {
  if (!iso) return '?';
  const at = new Date(iso);
  const time = at.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
  });
  if (at.toDateString() === new Date().toDateString()) return time;
  const day = at.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
  });
  return `${day} ${time}`;
}

function Reload() {
  return (
    <div className="update-banner">
      <span>
        Nouvelle version installée sur le serveur : recharge la page pour
        l’utiliser.
      </span>
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
  return `Mise à jour disponible (v${u.latest}) : ${count} — ${parts}.`;
}

function Install({ u, label }: { u: UpdateState; label: string }) {
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
        {label}
      </button>
      {ask.error && <span className="error">{ask.error.message}</span>}
    </>
  );
}

function Hide({ onHide }: { onHide: () => void }) {
  return (
    <button className="btn ghost" onClick={onHide}>
      Masquer
    </button>
  );
}

function Available(props: { u: UpdateState; later: () => void }) {
  const { u } = props;
  return (
    <div className="update-banner">
      <span>{what(u)}</span>
      <Install u={u} label="Installer" />
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

/** Asked or running, within the expected time. */
function Progress({ u }: { u: UpdateState }) {
  const text =
    u.state === 'requested'
      ? `Mise à jour demandée à ${hour(u.since)} : l’hôte la lance dans ` +
        'la minute.'
      : `Mise à jour en cours sur l’hôte depuis ${hour(u.since)} ` +
        '(1 à 5 min).';
  return (
    <div className="update-banner">
      {text} La page proposera ensuite de recharger.
    </div>
  );
}

function trouble(u: UpdateState): string {
  if (u.state === 'failed') return `La mise à jour a échoué : ${u.message}`;
  if (u.state === 'running') {
    return (
      `La mise à jour lancée à ${hour(u.since)} n’a pas donné de ` +
      'nouvelles depuis plus de 20 min.'
    );
  }
  return u.watcher
    ? `La demande de ${hour(u.since)} n’a pas été prise en charge.`
    : `La demande de ${hour(u.since)} attend : l’hôte ne surveille plus ` +
        'les demandes (cron inactif).';
}

/** Failed, or no news for too long: what to look at, ask again, hide. */
function Stuck({ u, onHide }: { u: UpdateState; onHide: () => void }) {
  return (
    <div className="update-banner failed">
      <span>{trouble(u)}</span>
      <span className="muted">
        Sur l’hôte : <code>{LOG}</code> <CopyButton text={LOG} />
      </span>
      <Install u={u} label="Relancer la mise à jour" />
      <Hide onHide={onHide} />
    </div>
  );
}

function Done({ u, onHide }: { u: UpdateState; onHide: () => void }) {
  return (
    <div className="update-banner done">
      <span>
        ✓ {u.message || 'À jour'} — installée à {hour(u.since)}.
      </span>
      <Hide onHide={onHide} />
    </div>
  );
}

function recent(u: UpdateState): boolean {
  const at = u.since ? Date.parse(u.since) : NaN;
  return Date.now() - at < RECENT_MS;
}

interface Seen {
  hidden: boolean;
  later: boolean;
  hide: () => void;
  postpone: () => void;
}

/** The administrator's banner: a problem or an update running first,
 * then one waiting, then « ✓ installée » (null: nothing to say). */
function adminBanner(u: UpdateState, seen: Seen): JSX.Element | null {
  const busy = ['requested', 'running'].includes(u.state);
  if (!seen.hidden && (u.state === 'failed' || u.stalled)) {
    return <Stuck u={u} onHide={seen.hide} />;
  }
  if (busy) return <Progress u={u} />;
  if (u.behind > 0 && !seen.later) {
    return <Available u={u} later={seen.postpone} />;
  }
  if (!seen.hidden && u.state === 'done' && recent(u)) {
    return <Done u={u} onHide={seen.hide} />;
  }
  return null;
}

function useSeen(u: UpdateState | undefined): Seen {
  const [later, setLater] = useState(readStored<string>('update.later'));
  const [hidden, setHidden] = useState(readStored<string>('update.hidden'));
  const key = `${u?.state}:${u?.since ?? ''}`;
  return {
    hidden: hidden === key,
    later: later === u?.latest,
    hide: () => {
      writeStored('update.hidden', key);
      setHidden(key);
    },
    postpone: () => {
      writeStored('update.later', u?.latest ?? '');
      setLater(u?.latest ?? '');
    },
  };
}

/** Everyone: a new build installed → reload. The administrator also:
 * an update waiting on GitHub, running, stuck or just installed. */
export function UpdateBanner() {
  const admin = useAuth().user?.role === 'admin';
  const u = useUpdateState(admin).data;
  const updating = ['requested', 'running'].includes(u?.state ?? '');
  const newer = useNewBuild(updating);
  const seen = useSeen(u);
  if (newer) return <Reload />;
  if (!admin || !u) return null;
  return adminBanner(u, seen);
}
