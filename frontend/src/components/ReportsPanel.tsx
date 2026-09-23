import { useCreateReport, useReports } from '../hooks/useReports';
import { ReportControls } from './ReportControls';
import { ReportsTable } from './ReportsTable';
import { SynthesisCard } from './SynthesisCard';

export function ReportsPanel() {
  const reports = useReports().data ?? [];
  const create = useCreateReport();
  return (
    <>
      <section className="card">
        <h2>Rapports</h2>
        <p className="muted">
          La synthèse clinique est rédigée par le modèle médical texte (ex.
          MedGemma 27B) à partir du dossier : maladies, traitements, résultats
          d’examens et leur évolution, marqueurs, poids, indicateurs Apple
          Santé, photos et documents. Elle est jointe au PDF clinique.
        </p>
        <ReportControls
          onCreate={(type, range) => create.mutate({ type, range })}
          busy={create.isPending}
        />
        <ReportsTable reports={reports} />
      </section>
      <SynthesisCard reports={reports} />
    </>
  );
}
