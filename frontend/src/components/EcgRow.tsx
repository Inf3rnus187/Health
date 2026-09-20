import type { EcgRow as Row } from '../api/types';
import { shortDateTime } from '../utils/datetime';
import { DownloadButton } from './DownloadButton';

export function EcgRow({ row }: { row: Row }) {
  return (
    <tr>
      <td>{shortDateTime(row.recorded_at)}</td>
      <td>{row.classification ?? '—'}</td>
      <td className="metric-type">{row.sample_rate_hz ?? '—'} Hz</td>
      <td className="metric-type">{row.sample_count ?? '—'} pts</td>
      <td>
        <DownloadButton
          path={`/ecg/${row.id}/file`}
          filename={`ecg_${row.id}.csv`}
          label="CSV"
        />
      </td>
    </tr>
  );
}
