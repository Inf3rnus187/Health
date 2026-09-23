import { EvidenceList } from './EvidenceList';
import { ProofForm } from './ProofForm';

/** Proofs (calls, mails…) and traces (transport, taxi, parking, meals…). */
export function EvidenceCard() {
  return (
    <section className="card">
      <h2>Preuves et traces</h2>
      <p className="muted">
        Preuves : appels, SMS, mails, captures. Traces : ce que des tiers ont
        enregistré — métro, taxi, parking, repas livré, hôtel, note de frais.
        Chaque fichier garde son empreinte SHA-256 (imprimée dans le rapport).
        Un fichier nommé avec sa date et son heure (« 2026-05-09 03h47.pdf », «
        09-05-2026_03.47.png ») remplit « Quand » tout seul.
      </p>
      <ProofForm />
      <EvidenceList />
    </section>
  );
}
