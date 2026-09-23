import { BiologyImport } from '../components/BiologyImport';
import { CdaImport } from '../components/CdaImport';
import { MedicalList } from '../components/MedicalList';
import { MedicalUpload } from '../components/MedicalUpload';
import { DicomViewer } from '../components/dicom/DicomViewer';
import { ResultsCard } from '../components/record/ResultsCard';
import { SuggestionsCard } from '../components/record/SuggestionsCard';
import { TimelineCard } from '../components/record/TimelineCard';
import { useStored } from '../utils/stored';

const TABS = {
  synthese: 'Synthèse',
  chronologie: 'Chronologie',
  documents: 'Documents',
  imagerie: 'Imagerie',
  importer: 'Importer',
};
type Tab = keyof typeof TABS;

function Documents() {
  return (
    <>
      <MedicalUpload />
      <section className="card">
        <h2>Documents</h2>
        <p className="muted">
          Ordonnances, imageries et comptes-rendus, prises de sang, EFR, tests
          de marche, dossier CDA… Chaque document est lu par le modèle médical :
          ses valeurs rejoignent vos courbes, ses diagnostics et médicaments
          sont proposés dans la Synthèse.
        </p>
        <MedicalList />
      </section>
    </>
  );
}

const PAGES: Record<Tab, () => JSX.Element> = {
  synthese: () => (
    <>
      <SuggestionsCard />
      <ResultsCard />
    </>
  ),
  chronologie: () => <TimelineCard />,
  documents: () => <Documents />,
  imagerie: () => <DicomViewer />,
  importer: () => (
    <>
      <BiologyImport />
      <CdaImport />
    </>
  ),
};

/** The medical record, one tab at a time (no endless page). */
export function MedicalPage() {
  const [tab, setTab] = useStored<Tab>(
    'dossier.tab',
    'synthese',
    Object.keys(TABS),
  );
  return (
    <>
      <div className="tabs">
        {(Object.entries(TABS) as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            className={key === tab ? 'tab active' : 'tab'}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {PAGES[tab]()}
    </>
  );
}
