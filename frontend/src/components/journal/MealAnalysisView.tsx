import type { Food } from '../../api/foods';
import type { MealAnalysis, MealItem } from '../../api/journal';
import type { MealReference } from '../../api/nutrition';
import { useFoods } from '../../hooks/useFoods';
import { frNumber } from '../../utils/format';
import { MealRefs } from './MealRefs';
import { NutrientTable } from './NutrientTable';
import { RefLink } from './RefLink';
import { LINKS } from './refLinks';

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

/** « Tomate, crue » out of « Ciqual 2025 · Tomate, crue ». */
function tableName(reference?: string): string {
  return reference?.split(' · ').slice(1).join(' · ') ?? '';
}

/** Where an item's values come from, after its grams, with its link. */
function Origin({ item, food }: { item: MealItem; food?: Food }) {
  if (item.source === 'étiquette') {
    const url = food?.product_info?.url;
    const label = 'étiquette 🏷️';
    return <>, {url ? <RefLink href={url}>{label}</RefLink> : label}</>;
  }
  if (item.source !== 'Ciqual') return <>, estimé</>;
  const name = tableName(item.reference);
  return (
    <>
      , <RefLink href={LINKS.ciqual}>Ciqual</RefLink>
      {name && ` « ${name} »`}
    </>
  );
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
  const { data: foods } = useFoods();
  const byId = new Map((foods ?? []).map((f) => [f.id, f]));
  const dropped = (a.rejected ?? []).map((r) => `${r.name} (${r.reason})`);
  return (
    <p className="muted">
      {(a.items ?? []).map((i, n) => (
        <span key={`${n}${i.name}`}>
          {n > 0 && ', '}
          {i.name} ({quantity(i)}
          <Origin item={i} food={byId.get(i.food_id ?? '')} />)
        </span>
      ))}
      {dropped.length > 0 && ` — écarté : ${dropped.join(', ')}`}
    </p>
  );
}

/** Which models read the meal, and what the verdict rests on. */
function Made({ a }: { a: MealAnalysis }) {
  return (
    <p className="muted small">
      Aliments : IA ({a.model}
      {a.vision_model ? ` + photo : ${a.vision_model}` : ''}) et ta description.
      Avis : écrit par l’IA d’après ces valeurs, chiffres vérifiés.
    </p>
  );
}

/** The checked reading of a meal: score, verdict, nutrients, foods. */
export function MealAnalysisView(props: {
  a: MealAnalysis;
  reference?: MealReference | null;
}) {
  const { a } = props;
  return (
    <div className="meal-analysis">
      <p>
        {a.score != null && (
          <span className={scoreClass(a.score)}>{frNumber(a.score, 1)}/10</span>
        )}{' '}
        {a.verdict}
      </p>
      <Remarks a={a} />
      {a.totals && (
        <NutrientTable totals={a.totals} reference={props.reference} />
      )}
      <Foods a={a} />
      <Made a={a} />
      <MealRefs />
    </div>
  );
}
