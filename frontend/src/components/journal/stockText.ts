import type { Food } from '../../api/foods';
import type { StockKind, StockLevel } from '../../api/stock';
import { frNumber } from '../../utils/format';

export const KINDS: Record<StockKind, string> = {
  purchase: 'Achat',
  out: 'Jeté / donné',
  count: 'Inventaire',
};

/** « 370 g (2 × 185 g) », « 720 g (≈ 6 tomate) », « épuisé ». */
export function stockText(level: StockLevel): string {
  if (level.grams <= 0) {
    return level.missing > 0
      ? `épuisé — les repas dépassent de ${frNumber(level.missing, 0)} g ` +
          'ce qui a été noté : faites l’inventaire'
      : 'épuisé';
  }
  const grams = `${frNumber(level.grams, 1)} g`;
  const { packs, package_g: pack, units } = level;
  if (packs != null && pack) {
    return `${grams} (${frNumber(packs, 1)} × ${frNumber(pack, 0)} g)`;
  }
  const unit = level.unit_name || 'unité';
  return units != null ? `${grams} (≈ ${frNumber(units, 1)} ${unit})` : grams;
}

export type Measure = 'packs' | 'units' | 'grams';

/** How a quantity of this food can be typed: packs, its unit, grams. */
export function measures(food: Food): [Measure, string][] {
  const out: [Measure, string][] = [];
  if (food.package_g) {
    out.push(['packs', 'boîte(s)']);
  }
  if (food.unit_g) out.push(['units', `${food.unit_name || 'unité'}(s)`]);
  out.push(['grams', 'grammes']);
  return out;
}

/** A date and time as « 25/09 18:40 ». */
export const when = (at: string) =>
  new Date(at).toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
