import { MedicalList } from '../components/MedicalList';
import { MedicalUpload } from '../components/MedicalUpload';

export function MedicalPage() {
  return (
    <>
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
