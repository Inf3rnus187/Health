import { useCreateReport, useReports } from '../hooks/useReports';
import { ReportControls } from './ReportControls';
import { ReportsTable } from './ReportsTable';
import { SynthesisCard } from './SynthesisCard';
import { VerifyReport } from './VerifyReport';

function About() {
  return (
    <p className="muted">
      La synthèse clinique est rédigée par le modèle médical texte (ex. MedGemma
      27B) à partir du dossier : maladies, traitements, résultats d’examens et
      leur évolution, marqueurs, poids, indicateurs Apple Santé, photos et
      documents. Elle est jointe au PDF clinique. Le PDF clinique prouve aussi
      les faits de la période : habitudes (jours sans saisie compris, avant /
      après une date), observance des médicaments, alimentation, et quand chaque
      saisie a été faite.
    </p>
  );
}

export function ReportsPanel() {
  const reports = useReports().data ?? [];
  const create = useCreateReport();
  return (
    <>
      <section className="card">
        <h2>Rapports</h2>
        <About />
        <ReportControls
          onCreate={(type, range, params) =>
            create.mutate({ type, range, params })
          }
          busy={create.isPending}
        />
        <ReportsTable reports={reports} />
        <VerifyReport />
      </section>
      <SynthesisCard reports={reports} />
    </>
  );
}
