import type { Report, Synthesis, SynthesisItem } from '../api/types';
import { shortDateTime } from '../utils/datetime';

function Refs({
  item,
  facts,
}: {
  item: SynthesisItem;
  facts: Synthesis['facts'];
}) {
  const byId = new Map(facts.map((f) => [f.id, f]));
  return (
    <>
      {item.facts.map((ref) => (
        <span key={ref} className="fact-ref" title={byId.get(ref)?.text ?? ''}>
          {ref}
        </span>
      ))}
    </>
  );
}

function Sections({ found }: { found: Synthesis }) {
  return (
    <>
      {found.sections
        .filter((s) => s.items.length > 0)
        .map((section) => (
          <div key={section.key}>
            <h3>{section.title}</h3>
            <ul className="synthesis-list">
              {section.items.map((item) => (
                <li key={item.text}>
                  {item.text} <Refs item={item} facts={found.facts} />
                </li>
              ))}
            </ul>
          </div>
        ))}
    </>
  );
}

function Annex({ found }: { found: Synthesis }) {
  return (
    <details>
      <summary className="muted">
        {found.facts.length} faits transmis au modèle · {found.rejected}{' '}
        phrase(s) retirée(s)
      </summary>
      <ul className="synthesis-facts">
        {found.rejected_items.map((r) => (
          <li key={r.text} className="error">
            Retirée : « {r.text} » — {r.reason}
          </li>
        ))}
        {found.facts.map((f) => (
          <li key={f.id}>
            <strong>{f.id}</strong> {f.section} — {f.text}
          </li>
        ))}
      </ul>
    </details>
  );
}

function latest(reports: Report[]): Report | undefined {
  return reports.find((r) => r.type === 'synthesis' && r.summary);
}

/** The newest AI clinical synthesis, every sentence with its facts. */
export function SynthesisCard({ reports }: { reports: Report[] }) {
  const report = latest(reports);
  const found = report?.summary;
  if (!report || !found) {
    return null;
  }
  return (
    <section className="card">
      <h2>Synthèse clinique ({found.model})</h2>
      <p className="muted">
        {shortDateTime(report.created_at)} — rédigée à partir des seules données
        du dossier ; survolez une référence pour voir le fait cité. À valider
        par un médecin : ni diagnostic ni prescription.
      </p>
      {found.error ? (
        <p className="error">Synthèse indisponible : {found.error}</p>
      ) : (
        <Sections found={found} />
      )}
      <Annex found={found} />
    </section>
  );
}
