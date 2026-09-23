import { api, getAccessToken } from './client';

export interface UrinationDay {
  day: string;
  count: number;
  items: { id: string; at: string }[];
}

export interface MealTotals {
  grams: number;
  energy_kcal: number;
  protein_g: number;
  carbs_g: number;
  sugars_g: number;
  fat_g: number;
  sat_fat_g: number;
  fiber_g: number;
  sodium_mg: number;
}

export interface MealItem extends MealTotals {
  name: string;
}

export interface MealAnalysis {
  error?: string;
  model?: string;
  vision_model?: string | null;
  items?: MealItem[];
  rejected?: { name: string; reason: string }[];
  totals?: MealTotals;
  score?: number | null;
  verdict?: string | null;
  positives?: string[];
  watch?: string[];
}

export interface Meal {
  id: string;
  eaten_at: string;
  date_key: string;
  meal_type: string;
  description: string;
  has_photo: boolean;
  analysis_status: string | null;
  analysis: MealAnalysis | null;
}

export const MEAL_TYPES: Record<string, string> = {
  breakfast: 'Petit-déjeuner',
  lunch: 'Déjeuner',
  snack: 'Collation',
  dinner: 'Dîner',
};

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const fetchUrinations = (day: string) =>
  api<UrinationDay>(`/journal/urination?day=${day}`);
export const logUrination = (at?: string) =>
  api<{ id: string; count: number }>(
    '/journal/urination',
    json('POST', { at }),
  );
export const deleteUrination = (id: string) =>
  api<{ detail: string }>(`/journal/urination/${id}`, json('DELETE'));

export const fetchMeals = (start: string, end: string) =>
  api<Meal[]>(`/meals?start=${start}&end=${end}`);
export const analyzeMeal = (id: string) =>
  api<{ status: string }>(`/meals/${id}/analyze`, json('POST'));
export const deleteMeal = (id: string) =>
  api<{ detail: string }>(`/meals/${id}`, json('DELETE'));

function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Log a meal (multipart: photo + fields); the AI reading is queued. */
export async function createMeal(form: FormData): Promise<Meal> {
  const res = await fetch('/api/v1/meals', {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(body?.detail ?? `Erreur ${res.status}`);
  }
  return (await res.json()) as Meal;
}

/** The meal photo as an object URL (authenticated). */
export async function fetchMealPhoto(id: string): Promise<string> {
  const res = await fetch(`/api/v1/meals/${id}/photo`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return URL.createObjectURL(await res.blob());
}
