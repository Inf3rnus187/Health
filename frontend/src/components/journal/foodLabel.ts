import type { Food } from '../../api/foods';
import { frNumber } from '../../utils/format';

/** The shares of a package a usual portion is said as. */
const SHARES: [number, string][] = [
  [1, 'tout'],
  [0.5, '½'],
  [1 / 3, '⅓'],
  [0.25, '¼'],
  [0.75, '¾'],
];

const grams = (value: number) => `${frNumber(value, 1)} g`;

/** « portion : ¼ (187,5 g) », « portion : tout (185 g) », « 150 g ». */
export function portionText(food: Food): string {
  const { portion_g: portion, package_g: pack } = food;
  if (!portion) return '';
  const share = pack
    ? SHARES.find(([part]) => Math.abs(portion / pack - part) < 0.01)
    : undefined;
  return share
    ? `portion : ${share[1]} (${grams(portion)})`
    : `portion : ${grams(portion)}`;
}

/** Name · brand · package: two sizes of one product never look alike. */
export function foodName(food: Food): string {
  const pack = food.package_g ? grams(food.package_g) : '';
  return [food.name, food.brand, pack].filter(Boolean).join(' · ');
}

/** The name, then the usual portion (for a list to choose from). */
export function foodLabel(food: Food): string {
  const portion = portionText(food);
  return portion ? `${foodName(food)} — ${portion}` : foodName(food);
}

/** By name, then the smaller package first. */
export function bySize(a: Food, b: Food): number {
  return (
    a.name.localeCompare(b.name, 'fr') ||
    (a.package_g ?? 0) - (b.package_g ?? 0)
  );
}
