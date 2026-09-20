import type { Report } from '../api/types';
import { ReportRow } from './ReportRow';

export function ReportsTable({ reports }: { reports: Report[] }) {
  if (reports.length === 0) {
    return <p className="muted">Aucun rapport pour le moment.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="data-table">
        <tbody>
          {reports.map((report) => (
            <ReportRow key={report.id} report={report} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
