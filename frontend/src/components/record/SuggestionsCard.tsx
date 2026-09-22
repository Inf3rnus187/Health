import { createCondition, createTreatment } from '../../api/care';
import type {
  DocRef,
  SuggestedCondition,
  SuggestedTreatment,
} from '../../api/record';
import { useCareMutation } from '../../hooks/useCare';
import { useRecord } from '../../hooks/useRecord';
import { shortDate } from '../../utils/format';
import { DocLinks } from './DocLink';

function readIn(docs: DocRef[]): string {
  const first = docs[0];
  return first ? `Lu dans : ${first.title} (${shortDate(first.date)})` : '';
}

function ConditionRow({ item }: { item: SuggestedCondition }) {
  const add = useCareMutation('conditions', createCondition);
  const body = {
    name: item.name,
    status: 'active',
    notes: readIn(item.documents),
  };
  return (
    <li>
      <span className="import-name">{item.name}</span>
      <DocLinks docs={item.documents} />
      <button
        className="btn ghost"
        disabled={add.isPending}
        onClick={() => add.mutate(body)}
      >
        Ajouter aux maladies
      </button>
    </li>
  );
}

function treatmentBody(item: SuggestedTreatment): Record<string, unknown> {
  return {
    name: item.name,
    dose: item.dose || null,
    frequency: item.frequency || null,
    start_date: item.documents[0]?.date ?? null,
    notes: readIn(item.documents),
  };
}

function TreatmentRow({ item }: { item: SuggestedTreatment }) {
  const add = useCareMutation('treatments', createTreatment);
  const desc = [item.dose, item.frequency].filter(Boolean).join(' · ');
  return (
    <li>
      <span className="import-name">{item.name}</span>
      {desc && <span className="muted">{desc}</span>}
      <DocLinks docs={item.documents} />
      <button
        className="btn ghost"
        disabled={add.isPending}
        onClick={() => add.mutate(treatmentBody(item))}
      >
        Ajouter aux traitements
      </button>
    </li>
  );
}

function Intro() {
  return (
    <p className="muted">
      Diagnostics et médicaments trouvés par l’IA dans vos comptes-rendus et
      ordonnances (le nom figure dans le document). Rien n’est ajouté sans votre
      accord.
    </p>
  );
}

/** What the documents say that the record does not hold yet. */
export function SuggestionsCard() {
  const record = useRecord().data;
  const conditions = record?.suggested_conditions ?? [];
  const treatments = record?.suggested_treatments ?? [];
  if (conditions.length + treatments.length === 0) {
    return null;
  }
  return (
    <section className="card">
      <h2>À confirmer — lu dans vos documents</h2>
      <Intro />
      <ul className="care-list">
        {conditions.map((item) => (
          <ConditionRow key={item.name} item={item} />
        ))}
        {treatments.map((item) => (
          <TreatmentRow key={item.name} item={item} />
        ))}
      </ul>
    </section>
  );
}
