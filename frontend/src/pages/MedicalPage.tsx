import { BiologyImport } from '../components/BiologyImport';
import { CdaImport } from '../components/CdaImport';
import { MedicalList } from '../components/MedicalList';
import { MedicalUpload } from '../components/MedicalUpload';
import { DicomViewer } from '../components/dicom/DicomViewer';

export function MedicalPage() {
  return (
    <>
      <BiologyImport />
      <CdaImport />
      <DicomViewer />
      <MedicalUpload />
      <section className="card">
        <h2>Dossier médical</h2>
        <p className="muted">
          Ordonnances, imageries et comptes-rendus, prises de sang, EFR, tests
          de marche, dossier CDA… à conserver et à remettre facilement à un
          soignant.
        </p>
        <MedicalList />
      </section>
    </>
  );
}
