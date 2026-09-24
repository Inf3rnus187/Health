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

/** The version of the page loaded: its commit and when it was built. */
export function AppVersion() {
  const built = stamp(__BUILD_ID__);
  const title = `Version de la page chargée (construite le ${built})`;
  if (!__COMMIT__) {
    return (
      <span className="app-version" title={title}>
        version du {built}
      </span>
    );
  }
  return (
    <span className="app-version" title={title}>
      v{__COMMIT__}
      <span className="wide-only"> · {built}</span>
    </span>
  );
}
