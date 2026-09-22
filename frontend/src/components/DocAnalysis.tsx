import type { DocAnalysis as Analysis, DocValue } from '../api/types';
import { frNumber, shortDate } from '../utils/format';

const STATUS: Record<string, string> = {
  queued: 'Lecture IA en cours…',
  done: 'Lu',
  failed: 'Échec de lecture',
};

function valueText(v: DocValue): string {
  const unit = v.unit ? ` ${v.unit}` : '';
  return `${v.label} : ${frNumber(v.value, 2)}${unit} (${shortDate(v.date)})`;
}

function Values({ values }: { values: DocValue[] }) {
  if (values.length === 0) {
    return <p className="muted">Aucune valeur mesurée trouvée.</p>;
  }
  return (
    <ul className="doc-values">
      {values.map((v) => (
        <li key={`${v.key}-${v.date}`}>
          {valueText(v)}
          <span className={`badge doc-origin-${v.origin}`}>
            {v.origin === 'ia' ? 'IA vérifiée' : 'lecture exacte'}
          </span>
        </li>
      ))}
    </ul>
  );
}

function Notes({ analysis }: { analysis: Analysis }) {
  const rejected = analysis.rejected ?? 0;
  return (
    <>
      {analysis.ai_error && (
        <p className="marker-missing">
          IA indisponible ({analysis.ai_error}) : seules les lectures exactes
          ont été enregistrées.
        </p>
      )}
      {rejected > 0 && (
        <p className="muted">
          {rejected} valeur(s) proposée(s) par l’IA rejetée(s) : nombre, date ou
          unité absents du document.
        </p>
      )}
    </>
  );
}

function Summary({ analysis }: { analysis: Analysis }) {
  if (!analysis.summary) {
    return null;
  }
  const model = analysis.model ? ` (${analysis.model})` : '';
  return (
    <p className="doc-summary">
      <strong>Résumé IA{model} :</strong> {analysis.summary}
    </p>
  );
}

function Body({ analysis }: { analysis: Analysis }) {
  return (
    <>
      {analysis.error && <p className="error">{analysis.error}</p>}
      <Summary analysis={analysis} />
      {analysis.values && <Values values={analysis.values} />}
      <Notes analysis={analysis} />
    </>
  );
}

export function DocAnalysis({
  status,
  analysis,
}: {
  status?: string | null;
  analysis?: Analysis | null;
}) {
  if (!status) {
    return null;
  }
  return (
    <div className="doc-analysis">
      <span className={`badge doc-status-${status}`}>
        {STATUS[status] ?? status}
      </span>
      {analysis && <Body analysis={analysis} />}
    </div>
  );
}
