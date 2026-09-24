import type { Food, FoodIn, LabelReading, Per100g } from '../../api/foods';

/** The label lines of the form: salt as printed (sodium is stored). */
export const VALUES = [
  ['energy_kcal', 'Énergie (kcal)'],
  ['protein_g', 'Protéines (g)'],
  ['carbs_g', 'Glucides (g)'],
  ['sugars_g', 'dont sucres (g)'],
  ['fat_g', 'Lipides (g)'],
  ['sat_fat_g', 'dont saturés (g)'],
  ['fiber_g', 'Fibres (g)'],
  ['salt_g', 'Sel (g)'],
] as const;

export type ValueKey = (typeof VALUES)[number][0];

/** The form as typed (text: « 12,5 » is fine). */
export interface FoodDraft {
  name: string;
  brand: string;
  aliases: string;
  package_g: string;
  note: string;
  values: Record<ValueKey, string>;
}

const SODIUM_PER_SALT = 400; // 1 g of salt = 400 mg of sodium

const text = (value: number | null | undefined, digits = 2) =>
  value == null ? '' : String(Number(value.toFixed(digits)));

function valuesOf(per: Per100g): Record<ValueKey, string> {
  const salt = per.sodium_mg == null ? null : per.sodium_mg / SODIUM_PER_SALT;
  const out = { salt_g: text(salt) } as Record<ValueKey, string>;
  for (const [key] of VALUES) {
    if (key !== 'salt_g') out[key] = text(per[key]);
  }
  return out;
}

const EMPTY = { aliases: '', note: '' };

export function draftOf(food: Food | LabelReading | null): FoodDraft {
  if (!food) {
    return {
      name: '',
      brand: '',
      package_g: '',
      ...EMPTY,
      values: valuesOf({}),
    };
  }
  const known = 'aliases' in food ? food : EMPTY;
  return {
    name: food.name,
    brand: food.brand,
    aliases: known.aliases,
    package_g: text(food.package_g),
    note: known.note,
    values: valuesOf(food.per_100g),
  };
}

/** What the AI read fills the blanks and replaces the values. */
export function withReading(draft: FoodDraft, read: LabelReading): FoodDraft {
  const found = draftOf(read);
  const values = { ...draft.values };
  for (const [key] of VALUES) {
    if (found.values[key] !== '') values[key] = found.values[key];
  }
  return {
    ...draft,
    name: draft.name || found.name,
    brand: draft.brand || found.brand,
    package_g: found.package_g || draft.package_g,
    values,
  };
}

const num = (value: string): number | null => {
  const parsed = Number.parseFloat(value.replace(',', '.'));
  return Number.isFinite(parsed) ? parsed : null;
};

export function foodIn(draft: FoodDraft): FoodIn {
  const per: Per100g = {};
  for (const [key] of VALUES) {
    const value = num(draft.values[key]);
    if (value == null) continue;
    if (key === 'salt_g') per.sodium_mg = Math.round(value * SODIUM_PER_SALT);
    else per[key] = value;
  }
  return {
    name: draft.name.trim(),
    brand: draft.brand.trim(),
    aliases: draft.aliases.trim(),
    package_g: num(draft.package_g),
    per_100g: per,
    note: draft.note.trim(),
  };
}
