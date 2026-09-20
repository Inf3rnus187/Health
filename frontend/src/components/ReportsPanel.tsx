import { useCreateReport, useReports } from '../hooks/useReports';
import { ReportControls } from './ReportControls';
import { ReportsTable } from './ReportsTable';

export function ReportsPanel() {
  const reports = useReports().data ?? [];
  const create = useCreateReport();
  return (
    <section className="card">
      <h2>Rapports</h2>
      <ReportControls
        onCreate={(type) => create.mutate(type)}
        busy={create.isPending}
      />
      <ReportsTable reports={reports} />
    </section>
  );
}
