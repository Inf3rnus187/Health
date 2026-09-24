// What meals paid for cost: Uber Eats and other deliveries, receipts.
import type { Range } from '../utils/range';
import { api } from './client';

export type SpendKind = 'livraison' | 'repas' | 'tout';
export type Bucket = 'auto' | 'day' | 'week' | 'month';

export interface SpendPeriod {
  /** First day of the day, week or month. */
  start: string;
  total: number;
  count: number;
}

export interface SpendHour {
  hour: number;
  count: number;
  total: number;
  /** Ordered from 21:00 to 04:59. */
  late: boolean;
}

export interface SpendVendor {
  name: string;
  count: number;
  total: number;
  /** Percent of the period's total. */
  share: number;
}

export interface MealSpending {
  start: string;
  end: string;
  bucket: Exclude<Bucket, 'auto'>;
  total: number;
  count: number;
  average: number | null;
  per_month: number | null;
  largest: { amount: number; name: string; at: string } | null;
  late: { count: number; total: number };
  periods: SpendPeriod[];
  hours: SpendHour[];
  vendors: SpendVendor[];
}

export function fetchMealSpending(
  range: Range,
  kind: SpendKind,
  bucket: Bucket,
): Promise<MealSpending> {
  const params = new URLSearchParams({ end: range.end, kind, bucket });
  if (range.start) params.set('start', range.start);
  return api<MealSpending>(`/spending/meals?${params.toString()}`);
}
