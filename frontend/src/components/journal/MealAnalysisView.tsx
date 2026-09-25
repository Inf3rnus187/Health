import type { MealAnalysis, MealItem, MealTotals } from '../../api/journal';
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

/** Where an item's values come from, as shown after its grams. */
function origin(source?: string): string {
  if (source === 'étiquette') return ', étiquette 🏷️';
  if (source === 'Ciqual') return ', Ciqual';
  return ', estimé';
}

/** How the grams were given, after them: « écrits », « ta portion »… */
const HOW: Record<string, string> = {
  écrit: ' écrits',
  compté: ' comptés',
  portion: ', ta portion',
  formulaire: ' saisis',
  paquet: ', le paquet',
  IA: ' estimés par l’IA',
  défaut: ' estimés',
};

/** « 240 g = 2 × 120 g, unité estimée par l'IA » or « 185 g, ta portion ». */
function quantity(i: MealItem): string {
  const grams = `${frNumber(i.grams, 0)} g`;
  if (i.grams_from === 'unités' && i.units) {
    return `${grams} = ${i.units}, unité estimée par l’IA`;
  }
  return `${grams}${HOW[i.grams_from ?? ''] ?? ''}`;
}

function Foods({ a }: { a: MealAnalysis }) {
  const kept = (a.items ?? []).map(
    (i) => `${i.name} (${quantity(i)}${origin(i.source)})`,
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
        Aliments : IA ({a.model}
        {a.vision_model ? ` + photo : ${a.vision_model}` : ''}) et votre
        description. Quantités : écrites ou comptées dans la description, vos
        fiches, sinon estimées par l’IA (dit sur chaque aliment). Valeurs : vos
        étiquettes 🏷️, la table Ciqual 2025 (ANSES), sinon estimées. Avis :
        écrit par l’IA d’après ces valeurs, chiffres vérifiés.
      </p>
    </div>
  );
}
