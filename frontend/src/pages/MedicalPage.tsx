import { BiologyImport } from '../components/BiologyImport';
import { CdaImport } from '../components/CdaImport';
import { MedicalList } from '../components/MedicalList';
import { MedicalUpload } from '../components/MedicalUpload';
import { DicomViewer } from '../components/dicom/DicomViewer';
import { ResultsCard } from '../components/record/ResultsCard';
import { SuggestionsCard } from '../components/record/SuggestionsCard';
import { TimelineCard } from '../components/record/TimelineCard';

export function MedicalPage() {
  return (
    <>
      <SuggestionsCard />
      <ResultsCard />
      <TimelineCard />
      <MedicalUpload />
      <section className="card">
        <h2>Documents</h2>
        <p className="muted">
          Ordonnances, imageries et comptes-rendus, prises de sang, EFR, tests
          de marche, dossier CDA… Chaque document est lu par le modèle médical :
          ses valeurs rejoignent vos courbes, ses diagnostics et médicaments
          sont proposés ci-dessus.
        </p>
        <MedicalList />
      </section>
      <BiologyImport />
      <CdaImport />
      <DicomViewer />
    </>
  );
}
