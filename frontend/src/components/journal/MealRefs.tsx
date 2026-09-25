import { useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { MEAL_TYPES } from '../../api/journal';
import {
  fetchNutritionReferences,
  type NutritionReferences,
} from '../../api/nutrition';
import { frNumber } from '../../utils/format';
import { RefLink } from './RefLink';
import { LINKS } from './refLinks';

const NAMES: Record<string, string> = {
  energy_kcal: 'énergie',
  protein_g: 'protéines',
  carbs_g: 'glucides',
  sugars_g: 'sucres',
  fat_g: 'lipides',
  sat_fat_g: 'saturés',
  fiber_g: 'fibres',
  sodium_mg: 'sodium',
};
const SIGN: Record<string, string> = { limit: '≤ ', target: '≥ ' };

/** « énergie 2 000 kcal (UE), …, sodium ≤ 2 000 mg (OMS) ». */
function daily(refs: NutritionReferences): string {
  return Object.entries(refs.daily)
    .map(
      ([key, d]) =>
        `${NAMES[key] ?? key} ${SIGN[d.kind] ?? ''}${frNumber(d.value)} ` +
        `${d.unit} (${d.source})`,
    )
    .join(', ');
}

/** « Petit-déjeuner 15–25 %, … ; collation : aucune ». */
function shares(refs: NutritionReferences): string {
  const parts = Object.entries(refs.share_pct).map(
    ([type, [low, high]]) =>
      `${(MEAL_TYPES[type] ?? type).toLowerCase()} ${low}–${high} %`,
  );
  return `${parts.join(', ')} ; collation : aucune part fixée`;
}

function Sources() {
  const { data } = useQuery({
    queryKey: ['nutrition-references'],
    queryFn: fetchNutritionReferences,
    staleTime: Infinity,
  });
  if (!data) return <dd>…</dd>;
  const text =
    `Par jour : ${daily(data)}. Part d’un repas (indicatif) : ` +
    `${shares(data)}. ${data.note}`;
  return (
    <dd>
      {text}
      <ul>
        {Object.entries(data.sources).map(([key, s]) => (
          <li key={key}>
            <RefLink href={s.url}>{s.name}</RefLink>
          </li>
        ))}
      </ul>
    </dd>
  );
}

/** Each term of a meal's result and what it means. */
const TERMS: [ReactNode, string][] = [
  [
    <>
      <RefLink href={LINKS.nutriscore}>Nutri-Score</RefLink> (A à E)
    </>,
    'Qualité nutritionnelle d’un produit pour 100 g, comparée à sa ' +
      'catégorie : A le plus favorable, E le moins. Compte ce qui est à ' +
      'favoriser (fibres, protéines, fruits et légumes) et à limiter ' +
      '(énergie, saturés, sucres, sel).',
  ],
  [
    <>
      <RefLink href={LINKS.nova}>NOVA</RefLink> (1 à 4)
    </>,
    'Degré de transformation, pas la valeur nutritionnelle : 1 brut ou ' +
      'peu transformé (légume, viande, lait) · 2 ingrédient culinaire ' +
      '(huile, beurre, sel) · 3 transformé (conserve, fromage, pain : un ' +
      'aliment 1 avec des ingrédients 2) · 4 ultra-transformé (additifs, ' +
      'ingrédients industriels : arômes, émulsifiants…).',
  ],
  [
    <RefLink href={LINKS.ciqual}>Ciqual 2025</RefLink>,
    'Table de composition des aliments de l’ANSES, livrée avec le hub ' +
      '(hors ligne) : les valeurs d’un aliment moyen, pas d’une marque. ' +
      'Après chaque aliment, entre « », l’aliment de la table utilisé.',
  ],
  [
    'Étiquette 🏷️',
    'Ta fiche dans Mes aliments (étiquette lue ou Open Food Facts) : les ' +
      'valeurs de ce produit-là. Le lien ouvre sa page Open Food Facts.',
  ],
  [
    'Estimé',
    'Ni fiche ni Ciqual : valeurs proposées par l’IA, les moins sûres.',
  ],
  [
    'Quantités',
    'écrits : tes grammes · 2 × 120 g : le nombre dit × le poids d’une ' +
      'unité estimé par l’IA · ta portion : celle de ta fiche · le paquet ' +
      '· estimés par l’IA : d’après la photo et la description.',
  ],
];

/** What each reference of a meal's result means, with its source. */
export function MealRefs() {
  return (
    <details className="meal-refs">
      <summary>Comprendre ces références</summary>
      <dl>
        <dt>Repères de la colonne de droite</dt>
        <Sources />
        {TERMS.map(([term, text], n) => (
          <div key={n}>
            <dt>{term}</dt>
            <dd>{text}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
