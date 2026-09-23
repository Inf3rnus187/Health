import type { MealAnalysis, MealTotals } from '../../api/journal';
import { frNumber } from '../../utils/format';

const ROWS: [keyof MealTotals, string, string][] = [
  ['energy_kcal', 'Énergie', 'kcal'],
  ['protein_g', 'Protéines', 'g'],
  ['carbs_g', 'Glucides', 'g'],
  ['sugars_g', '— dont sucres', 'g'],
  ['fat_g', 'Lipides', 'g'],
  ['sat_fat_g', '— dont saturés', 'g'],
  ['fiber_g', 'Fibres', 'g'],
  ['sodium_mg', 'Sodium', 'mg'],
];

export function NutrientTable({ totals }: { totals: MealTotals }) {
  return (
    <table className="nutri-table">
      <tbody>
        {ROWS.map(([key, label, unit]) => (
          <tr key={key}>
            <td>{label}</td>
            <td>
              {frNumber(totals[key], key === 'energy_kcal' ? 0 : 1)} {unit}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function scoreClass(score: number): string {
  if (score >= 7) return 'badge badge-done';
  if (score >= 4) return 'badge badge-warn';
  return 'badge badge-high';
}

function Remarks({ a }: { a: MealAnalysis }) {
  return (
    <ul className="meal-remarks">
      {(a.positives ?? []).map((text) => (
        <li key={`+${text}`}>✔ {text}</li>
      ))}
      {(a.watch ?? []).map((text) => (
        <li key={`!${text}`}>⚠ {text}</li>
      ))}
    </ul>
  );
}

function Foods({ a }: { a: MealAnalysis }) {
  const kept = (a.items ?? []).map(
    (i) => `${i.name} (${frNumber(i.grams, 0)} g)`,
  );
  const dropped = (a.rejected ?? []).map((r) => `${r.name} (${r.reason})`);
  return (
    <p className="muted">
      {kept.join(', ')}
      {dropped.length > 0 && ` — écarté : ${dropped.join(', ')}`}
    </p>
  );
}

/** The checked reading of a meal: score, verdict, nutrients, foods. */
export function MealAnalysisView({ a }: { a: MealAnalysis }) {
  return (
    <div className="meal-analysis">
      <p>
        {a.score != null && (
          <span className={scoreClass(a.score)}>{frNumber(a.score, 1)}/10</span>
        )}{' '}
        {a.verdict}
      </p>
      <Remarks a={a} />
      {a.totals && <NutrientTable totals={a.totals} />}
      <Foods a={a} />
      <p className="muted small">
        Estimation IA ({a.model}
        {a.vision_model ? ` + photo : ${a.vision_model}` : ''}) — indicative,
        énergie recalculée depuis les macronutriments.
      </p>
    </div>
  );
}
