import type { RouteRow } from '../api/types';
import { useRoutes } from '../hooks/useRecords';
import { shortDateTime } from '../utils/datetime';
import { DownloadButton } from './DownloadButton';

function Row({ row }: { row: RouteRow }) {
  return (
    <tr>
      <td>{shortDateTime(row.started_at)}</td>
      <td className="metric-type">{row.point_count} points</td>
      <td>
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
  if (rows.length === 0) {
    return null;
  }
  return (
    <section className="card">
      <h2>Tracés GPS ({rows.length})</h2>
      <div className="table-wrap scroll-y">
        <table className="data-table">
          <tbody>
            {rows.map((row) => (
              <Row key={row.id} row={row} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
