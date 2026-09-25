import { useQuery } from '@tanstack/react-query';

import { fetchHubVersion } from '../api/system';

const EVERY_5_MIN = 5 * 60 * 1000;

/** « 24/09 01:12 » from an ISO time. */
function stamp(iso: string): string {
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return '';
  const day = at.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
  });
  const time = at.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
  });
  return `${day} ${time}`;
}

/** The tip: the hub's version and when, then the page's own build. */
function tip(commit: string | null, when: string | null): string {
  const page = __COMMIT__ ? `v${__COMMIT__}` : 'sans numéro';
  const hub = commit ? ` : ${commit}` : '';
  const at = when ? `, le ${when}` : '';
  return (
    `Version installée sur le hub${hub}${at} · page chargée : ${page}, ` +
    `construite le ${stamp(__BUILD_ID__)}`
  );
}

/** The version the hub runs, and when it was installed. An update of the
 * server alone does not rebuild the page, whose own build is in the tip. */
export function AppVersion() {
  const hub = useQuery({
    queryKey: ['hub-version'],
    queryFn: fetchHubVersion,
    refetchInterval: EVERY_5_MIN,
  }).data;
  const commit = hub?.commit ?? (__COMMIT__ || null);
  const installed = hub?.installed_at ? stamp(hub.installed_at) : null;
  const when = installed ?? stamp(__BUILD_ID__);
  return (
    <span className="app-version" title={tip(commit, installed)}>
      {commit ? `v${commit}` : `version du ${when}`}
      {commit && <span className="wide-only"> · {when}</span>}
    </span>
  );
}
