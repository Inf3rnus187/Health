import type { Report } from '../api/types';
import { shortDateTime } from '../utils/datetime';
import { shortDate } from '../utils/format';
import { DownloadButton } from './DownloadButton';
import { FileButtons } from './FileButtons';

const EXT: Record<string, string> = {
  synthesis: 'pdf',
  clinical_pdf: 'pdf',
  work: 'pdf',
  work_health: 'pdf',
  csv: 'csv',
  json: 'json',
  xlsx: 'xlsx',
  fhir: 'json',
};

const TYPE_LABEL: Record<string, string> = {
  synthesis: 'Synthèse clinique IA',
  clinical_pdf: 'PDF clinique',
  work: 'Heures travaillées',
  work_health: 'Dossier travail ↔ santé',
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

/** The report's period, e.g. "du 01/01/2026 au 31/03/2026". */
function period(report: Report): string {
  if (!report.period_end) return 'tout';
  const end = shortDate(report.period_end);
  if (!report.period_start) return `jusqu’au ${end}`;
  return `du ${shortDate(report.period_start)} au ${end}`;
}

function Status({ report }: { report: Report }) {
  return (
    <td className="metric-type">
      {STATUS[report.status] ?? report.status}
      {report.sha256 && (
        <div className="muted small" title={`SHA-256 : ${report.sha256}`}>
          empreinte {report.sha256.slice(0, 12)}…
        </div>
      )}
    </td>
  );
}

function File({ report }: { report: Report }) {
  const ext = EXT[report.type] ?? 'bin';
  if (report.status !== 'ready') return <td />;
  const path = `/reports/${report.id}/file`;
  const filename = `rapport_${report.id}.${ext}`;
  return (
    <td>
      {ext === 'pdf' ? (
        <FileButtons path={path} filename={filename} />
      ) : (
        <DownloadButton path={path} filename={filename} />
      )}
    </td>
  );
}

export function ReportRow({ report }: { report: Report }) {
  return (
    <tr>
      <td>{shortDateTime(report.created_at)}</td>
      <td>{TYPE_LABEL[report.type] ?? report.type}</td>
      <td className="muted">{period(report)}</td>
      <Status report={report} />
      <File report={report} />
    </tr>
  );
}
