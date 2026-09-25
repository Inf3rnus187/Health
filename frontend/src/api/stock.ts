import { api } from './client';

/** What is left of one food (grams never below 0). */
export interface StockLevel {
  food_id: string;
  name: string;
  grams: number;
  /** How much the meals exceed what was entered: a count sets it right. */
  missing: number;
  eaten_g: number;
  package_g: number | null;
  packs: number | null;
  unit_name: string;
  units: number | null;
  portion_g: number | null;
  portions: number | null;
  counted_at: string | null;
  last_purchase: string | null;
}

export type StockKind = 'purchase' | 'out' | 'count';

/** A purchase, a loss or a count: one of packs, units or grams. */
export interface StockIn {
  food_id: string;
  kind: StockKind;
  packs?: number;
  units?: number;
  grams?: number;
}

export interface StockMove {
  id: string;
  food_id: string;
  at: string;
  kind: StockKind;
  grams: number;
  said: string;
  source: string;
}

export interface StockHistory {
  moves: StockMove[];
  eaten: { meal_id: string; eaten_at: string; grams: number }[];
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const fetchStock = () =>
  api<{ foods: StockLevel[]; pending_meals: number }>('/stock');
export const addStock = (body: StockIn) =>
  api<{ move: StockMove; level: StockLevel }>('/stock', json('POST', body));
export const fetchStockHistory = (foodId: string) =>
  api<StockHistory>(`/stock/${foodId}/moves`);
export const deleteStockMove = (id: string) =>
  api<{ detail: string }>(`/stock/moves/${id}`, json('DELETE'));
