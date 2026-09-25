import type { ProductInfo } from '../../api/foods';
import { frNumber } from '../../utils/format';

const NOVA: Record<number, string> = {
  1: 'NOVA 1 · peu ou pas transformé',
  2: 'NOVA 2 · ingrédient culinaire',
  3: 'NOVA 3 · transformé',
  4: 'NOVA 4 · ultra-transformé',
};

const LEVEL_NAMES: Record<string, string> = {
  fat: 'matières grasses',
  'saturated-fat': 'saturés',
  sugars: 'sucres',
  salt: 'sel',
};
const LEVELS: Record<string, string> = {
  low: 'faible',
  moderate: 'modéré',
  high: 'élevé',
};

/** The 14 allergens of the regulation, in French. */
const ALLERGENS: Record<string, string> = {
  gluten: 'gluten',
  crustaceans: 'crustacés',
  eggs: 'œufs',
  fish: 'poisson',
  peanuts: 'arachides',
  soybeans: 'soja',
  milk: 'lait',
  nuts: 'fruits à coque',
  celery: 'céleri',
  mustard: 'moutarde',
  'sesame seeds': 'sésame',
  'sulphur dioxide and sulphites': 'sulfites',
  lupin: 'lupin',
  molluscs: 'mollusques',
};

const NUTRIENTS: Record<string, string> = {
  potassium: 'potassium',
  calcium: 'calcium',
  iron: 'fer',
  magnesium: 'magnésium',
  phosphorus: 'phosphore',
  zinc: 'zinc',
  cholesterol: 'cholestérol',
  'trans-fat': 'acides gras trans',
  'monounsaturated-fat': 'AG mono-insaturés',
  'polyunsaturated-fat': 'AG poly-insaturés',
  'omega-3-fat': 'oméga-3',
  starch: 'amidon',
  'added-sugars': 'sucres ajoutés',
  polyols: 'polyols',
  lactose: 'lactose',
  caffeine: 'caféine',
  'vitamin-c': 'vitamine C',
  'vitamin-d': 'vitamine D',
  'vitamin-b12': 'vitamine B12',
};

/** « Nutri-Score B · NOVA 3 · transformé · fruits et légumes 96 % ». */
export function productSummary(p: ProductInfo): string {
  return [
    p.nutriscore && `Nutri-Score ${p.nutriscore.toUpperCase()}`,
    p.nova != null && NOVA[p.nova],
    p.fruits_veg_pct != null &&
      `fruits et légumes ${frNumber(p.fruits_veg_pct, 0)} %`,
  ]
    .filter(Boolean)
    .join(' · ');
}

export const allergens = (tags: string[]) =>
  tags.map((t) => ALLERGENS[t] ?? t).join(', ');

/** « sel : modéré · saturés : faible… ». */
export const levels = (found: Record<string, string>) =>
  Object.entries(found)
    .map(([k, v]) => `${LEVEL_NAMES[k] ?? k} : ${LEVELS[v] ?? v}`)
    .join(' · ');

/** Grams per 100 g shown as g, mg or µg. */
function amount(grams: number): string {
  if (grams >= 1) return `${frNumber(grams, 1)} g`;
  if (grams >= 0.001) return `${frNumber(grams * 1000, 1)} mg`;
  return `${frNumber(grams * 1e6, 1)} µg`;
}

/** « potassium 210 mg, vitamine C 4 mg » for 100 g. */
export const others = (found: Record<string, number>) =>
  Object.entries(found)
    .map(([k, v]) => `${NUTRIENTS[k] ?? k.replace(/-/g, ' ')} ${amount(v)}`)
    .join(', ');

const CHANGED: Record<string, string> = {
  energy_kcal: 'énergie',
  protein_g: 'protéines',
  carbs_g: 'glucides',
  sugars_g: 'sucres',
  fat_g: 'lipides',
  sat_fat_g: 'saturés',
  fiber_g: 'fibres',
  sodium_mg: 'sodium',
  product_info: 'infos produit',
  package_g: 'poids',
  brand: 'marque',
};

/** « Mis à jour : sodium, infos produit » or « À jour ». */
export const changedText = (changed: string[]) =>
  changed.length
    ? `Mis à jour : ${changed.map((c) => CHANGED[c] ?? c).join(', ')}`
    : 'À jour : rien n’a changé';
