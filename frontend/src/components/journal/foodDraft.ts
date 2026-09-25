import type {
  CiqualRef,
  Food,
  FoodIn,
  LabelReading,
  Per100g,
} from '../../api/foods';

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
  unit_name: string;
  unit_g: string;
  portion_g: string;
  note: string;
  source: string;
  barcode: string;
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

const BLANK: LabelReading = {
  name: '',
  brand: '',
  package_g: null,
  per_100g: {},
};
type Own = Pick<
  Food,
  'aliases' | 'note' | 'unit_name' | 'unit_g' | 'portion_g'
>;
const EMPTY: Own = {
  aliases: '',
  note: '',
  unit_name: '',
  unit_g: null,
  portion_g: null,
};

/** The sheet of a saved food, of a reading (label, barcode), or blank. */
export function draftOf(food: Food | LabelReading | null): FoodDraft {
  const read: LabelReading = food ?? BLANK;
  const known: Own = food && 'aliases' in food ? food : EMPTY;
  return {
    name: read.name,
    brand: read.brand,
    aliases: known.aliases,
    package_g: text(read.package_g),
    unit_name: known.unit_name,
    unit_g: text(known.unit_g),
    portion_g: text(known.portion_g),
    note: known.note,
    source: read.source ?? '',
    barcode: read.barcode ?? '',
    values: valuesOf(read.per_100g),
  };
}

/** A Ciqual food: its values, its name when the sheet has none. */
export function withCiqual(draft: FoodDraft, ref: CiqualRef): FoodDraft {
  const per: Per100g = {};
  for (const [key, value] of Object.entries(ref.per_100g)) {
    if (value != null) per[key as keyof Per100g] = value;
  }
  return {
    ...draft,
    name: draft.name || (ref.name.split(',')[0] ?? ref.name),
    values: valuesOf(per),
    source: `Ciqual 2025 · ${ref.code} · ${ref.name}`,
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
    source: read.source ?? 'étiquette',
    barcode: read.barcode ?? draft.barcode,
    values,
  };
}

export const num = (value: string): number | null => {
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
    unit_name: draft.unit_name.trim(),
    unit_g: num(draft.unit_g),
    portion_g: num(draft.portion_g),
    per_100g: per,
    note: draft.note.trim(),
    source: draft.source.trim() || 'saisie',
    barcode: draft.barcode.replace(/\D/g, ''),
  };
}
