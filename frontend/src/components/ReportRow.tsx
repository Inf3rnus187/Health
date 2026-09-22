import type { Report } from '../api/types';
import { shortDateTime } from '../utils/datetime';
import { DownloadButton } from './DownloadButton';

const EXT: Record<string, string> = {
  synthesis: 'pdf',
  clinical_pdf: 'pdf',
  csv: 'csv',
  json: 'json',
  xlsx: 'xlsx',
  fhir: 'json',
};

const TYPE_LABEL: Record<string, string> = {
  synthesis: 'Synthèse clinique IA',
  clinical_pdf: 'PDF clinique',
  csv: 'CSV',
  json: 'JSON',
  xlsx: 'Excel',
  fhir: 'FHIR',
};
const STATUS: Record<string, string> = {
  pending: 'en cours…',
  ready: 'prêt',
  error: 'erreur',
};

export function ReportRow({ report }: { report: Report }) {
  const ext = EXT[report.type] ?? 'bin';
  return (
    <tr>
      <td>{shortDateTime(report.created_at)}</td>
      <td>{TYPE_LABEL[report.type] ?? report.type}</td>
      <td className="metric-type">{STATUS[report.status] ?? report.status}</td>
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
