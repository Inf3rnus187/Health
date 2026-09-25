import type { Range } from '../utils/range';
import { api, authFetch, toError } from './client';
import type { FoodPortion } from './foods';
import type { MealReference } from './nutrition';

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
  /** « étiquette »: computed from a food of « Mes aliments ». */
  source?: string;
  food_id?: string;
  /** How its grams were given: écrit, compté, portion, formulaire,
   * paquet, IA (the model's estimate), défaut. */
  grams_from?: string;
  /** « 2 × 120 g »: the count said × the model's weight of one unit. */
  units?: string;
  /** « Ciqual 2025 · Tomate, crue »: the table food its values are of. */
  reference?: string;
}

export interface MealAnalysis {
  error?: string;
  model?: string;
  vision_model?: string | null;
  items?: MealItem[];
  rejected?: { name: string; reason: string }[];
  /** The foods of « Mes aliments » used (picked or named). */
  foods?: string[];
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
  price: number | null;
  vendor: string;
  has_photo: boolean;
  /** The other photos (the box, the sachet, its values…). */
  photo_ids: string[];
  foods: FoodPortion[];
  analysis_status: string | null;
  analysis: MealAnalysis | null;
  /** Its totals against official daily references (by the hub). */
  reference?: MealReference | null;
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

export const fetchMeals = (range: Range) =>
  api<Meal[]>(`/meals?start=${range.start || '2000-01-01'}&end=${range.end}`);
export const analyzeMeal = (id: string) =>
  api<{ status: string }>(`/meals/${id}/analyze`, json('POST'));
export const deleteMeal = (id: string) =>
  api<{ detail: string }>(`/meals/${id}`, json('DELETE'));

/** Log a meal (multipart: photo + fields); the AI reading is queued. */
export async function createMeal(form: FormData): Promise<Meal> {
  const res = await authFetch('/meals', { method: 'POST', body: form });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(body?.detail ?? `Erreur ${res.status}`);
  }
  return (await res.json()) as Meal;
}

export const mealPhotoPath = (id: string, photoId: string) =>
  `/meals/${id}/photos/${photoId}`;

/** What a meal's edit changes (then it is read again). */
export interface MealChange {
  meal_type: string;
  eaten_at: string;
  description: string;
  foods: FoodPortion[];
}

export const updateMeal = (id: string, change: MealChange) =>
  api<Meal>(`/meals/${id}`, json('PUT', change));

/** Drop a photo: the plate's (``null``) or another; no reading yet. */
export const dropMealPhoto = (id: string, photoId: string | null) =>
  api<Meal>(
    photoId
      ? `/meals/${id}/photos/${photoId}?read=false`
      : `/meals/${id}/photo?read=false`,
    json('DELETE'),
  );

/** Add a photo (the plate's if it has none); no reading yet. */
export async function addMealPhoto(id: string, file: File): Promise<Meal> {
  const form = new FormData();
  form.set('file', file);
  const res = await authFetch(`/meals/${id}/photos?read=false`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw await toError(res);
  return (await res.json()) as Meal;
}

/** The meal photo as an object URL (authenticated). */
export async function fetchMealPhoto(id: string): Promise<string> {
  const res = await authFetch(`/meals/${id}/photo`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return URL.createObjectURL(await res.blob());
}
