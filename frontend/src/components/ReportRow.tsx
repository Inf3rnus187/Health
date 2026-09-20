import type { Report } from '../api/types';
import { shortDateTime } from '../utils/datetime';
import { DownloadButton } from './DownloadButton';

const EXT: Record<string, string> = {
  clinical_pdf: 'pdf',
  csv: 'csv',
  json: 'json',
  xlsx: 'xlsx',
  fhir: 'json',
};

export function ReportRow({ report }: { report: Report }) {
  const ext = EXT[report.type] ?? 'bin';
  return (
    <tr>
      <td>{shortDateTime(report.created_at)}</td>
      <td className="metric-key">{report.type}</td>
      <td className="metric-type">{report.status}</td>
      <td>
        {report.status === 'ready' && (
          <DownloadButton
            path={`/reports/${report.id}/file`}
            filename={`rapport_${report.id}.${ext}`}
          />
        )}
      </td>
    </tr>
  );
}
