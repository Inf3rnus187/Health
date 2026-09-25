import { api } from './client';
import type { MealTotals } from './journal';

/** « limit »: not to exceed; « target »: to reach; « reference »: a
 * benchmark, neither. */
export type RefKind = 'limit' | 'target' | 'reference';

/** One nutrient of a meal against the day's official reference. */
export interface ReferenceRow {
  /** The reference for a day (adult-type) and its unit. */
  day: number;
  unit: string;
  kind: RefKind;
  /** UE, ANSES or OMS. */
  source: string;
  /** The meal's share of the day's reference, in %. */
  day_pct: number;
  /** The meal type's indicative part of that day (none for a snack). */
  low?: number;
  high?: number;
  verdict?: 'below' | 'within' | 'above';
}

/** A meal's totals against the references, computed by the hub. */
export interface MealReference {
  meal_type: string;
  /** The meal type's part of the day, in % (null: a snack). */
  share_pct: [number, number] | null;
  rows: Partial<Record<keyof MealTotals, ReferenceRow>>;
}

/** Every reference, the meal parts and their sources. */
export interface NutritionReferences {
  daily: Record<
    string,
    { value: number; unit: string; kind: RefKind; source: string }
  >;
  share_pct: Record<string, [number, number]>;
  sources: Record<string, { name: string; url: string }>;
  note: string;
}

export const fetchNutritionReferences = () =>
  api<NutritionReferences>('/nutrition/references');
