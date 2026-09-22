import type {
  DocAnalysis as Analysis,
  DocMedication,
  DocRejected,
  DocValue,
} from '../api/types';
import { frNumber, shortDate } from '../utils/format';

const STATUS: Record<string, string> = {
  queued: 'En file d’attente…',
  running: 'Lecture IA en cours…',
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

function medText(med: DocMedication): string {
  return [med.name, med.dose, med.frequency].filter(Boolean).join(' · ');
}

function Lists({ analysis }: { analysis: Analysis }) {
  const meds = analysis.medications ?? [];
  const conditions = analysis.conditions ?? [];
  return (
    <>
      {meds.length > 0 && (
        <p className="doc-line">
          <strong>Médicaments :</strong> {meds.map(medText).join(' ; ')}
        </p>
      )}
      {conditions.length > 0 && (
        <p className="doc-line">
          <strong>Diagnostics mentionnés :</strong> {conditions.join(' ; ')}
        </p>
      )}
    </>
  );
}

function Summary({ analysis }: { analysis: Analysis }) {
  if (!analysis.summary) {
    return null;
  }
  const model = analysis.summary_model ? ` — ${analysis.summary_model}` : '';
  return (
    <div className="doc-summary">
      <strong>Résumé IA (non vérifié{model}) :</strong> {analysis.summary}
      {(analysis.findings ?? []).length > 0 && (
        <ul className="doc-findings">
          {(analysis.findings ?? []).map((finding) => (
            <li key={finding}>{finding}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function rejectedText(item: DocRejected): string {
  const what = [item.key, item.value, item.unit, item.date]
    .filter(Boolean)
    .join(' ');
  return `${what} → ${item.reason}`;
}

function Rejected({ analysis }: { analysis: Analysis }) {
  const items = analysis.rejected_items ?? [];
  if ((analysis.rejected ?? 0) === 0) {
    return null;
  }
  return (
    <details className="doc-rejected">
      <summary className="muted">
        {analysis.rejected} proposition(s) de l’IA rejetée(s) (non prouvées par
        le document)
      </summary>
      <ul>
        {items.map((item, index) => (
          <li key={index}>{rejectedText(item)}</li>
        ))}
      </ul>
    </details>
  );
}

function Meta({ analysis }: { analysis: Analysis }) {
  const parts = [
    analysis.model ? `valeurs : ${analysis.model}` : '',
    analysis.duration_s != null ? `${analysis.duration_s} s` : '',
    analysis.scanned ? 'scanné (OCR)' : '',
  ].filter(Boolean);
  return (
    <>
      {analysis.ai_error && (
        <p className="marker-missing">
          IA partiellement indisponible ({analysis.ai_error}) : les lectures
          exactes sont enregistrées.
        </p>
      )}
      {parts.length > 0 && (
        <p className="muted doc-line">{parts.join(' · ')}</p>
      )}
    </>
  );
}

function Body({ analysis }: { analysis: Analysis }) {
  return (
    <>
      {analysis.error && <p className="error">{analysis.error}</p>}
      {analysis.values && <Values values={analysis.values} />}
      <Summary analysis={analysis} />
      <Lists analysis={analysis} />
      <Rejected analysis={analysis} />
      <Meta analysis={analysis} />
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
