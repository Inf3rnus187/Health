import { useState } from 'react';

import type { RouteRow } from '../api/types';
import { useRoutes } from '../hooks/useRecords';
import { shortDateTime } from '../utils/datetime';
import { DownloadButton } from './DownloadButton';
import { PagedRows } from './PagedRows';
import { RouteViewer } from './RouteViewer';

function Row({ row, onView }: { row: RouteRow; onView: (id: string) => void }) {
  return (
    <tr>
      <td>{shortDateTime(row.started_at)}</td>
      <td className="metric-type">{row.point_count} points</td>
      <td className="row-actions">
        <button className="btn ghost" onClick={() => onView(row.id)}>
          Voir
        </button>
        <DownloadButton
          path={`/routes/${row.id}/file`}
          filename={`route_${row.id}.gpx`}
          label="GPX"
        />
      </td>
    </tr>
  );
}

export function RoutesCard() {
  const rows = useRoutes().data ?? [];
  const [selected, setSelected] = useState<string | null>(null);
  if (rows.length === 0) {
    return null;
  }
  return (
    <section className="card">
      <h2>Tracés GPS ({rows.length})</h2>
      <PagedRows
        items={rows}
        row={(row) => <Row key={row.id} row={row} onView={setSelected} />}
      />
      {selected && (
        <RouteViewer id={selected} onClose={() => setSelected(null)} />
      )}
    </section>
  );
}
