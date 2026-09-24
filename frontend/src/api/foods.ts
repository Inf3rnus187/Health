import { api, authFetch, toError } from './client';

/** What 100 g contain, from the manufacturer's label. */
export interface Per100g {
  energy_kcal?: number;
  protein_g?: number;
  carbs_g?: number;
  sugars_g?: number;
  fat_g?: number;
  sat_fat_g?: number;
  fiber_g?: number;
  sodium_mg?: number;
}

export type PhotoKind = 'pack' | 'label';

export interface FoodIn {
  name: string;
  brand: string;
  aliases: string;
  package_g: number | null;
  per_100g: Per100g;
  note: string;
}

export interface Food extends FoodIn {
  id: string;
  photos: { id: string; kind: PhotoKind }[];
  created_at: string;
}

/** What the AI read on a label: a proposal to check. */
export interface LabelReading {
  name: string;
  brand: string;
  package_g: number | null;
  per_100g: Per100g;
}

/** A catalogue food in a meal (grams: null → the AI estimates). */
export interface FoodPortion {
  food_id: string;
  grams: number | null;
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const fetchFoods = () => api<Food[]>('/foods');
export const createFood = (body: FoodIn) =>
  api<Food>('/foods', json('POST', body));
export const updateFood = (id: string, body: FoodIn) =>
  api<Food>(`/foods/${id}`, json('PUT', body));
export const deleteFood = (id: string) =>
  api<{ detail: string }>(`/foods/${id}`, json('DELETE'));
export const deleteFoodPhoto = (id: string, photoId: string) =>
  api<Food>(`/foods/${id}/photos/${photoId}`, json('DELETE'));
export const foodPhotoPath = (id: string, photoId: string) =>
  `/foods/${id}/photos/${photoId}`;

async function send<T>(path: string, form: FormData): Promise<T> {
  const res = await authFetch(path, { method: 'POST', body: form });
  if (!res.ok) throw await toError(res);
  return (await res.json()) as T;
}

/** Add a photo of the box (pack) or of its nutrition values (label). */
export function addFoodPhoto(id: string, file: File, kind: PhotoKind) {
  const form = new FormData();
  form.set('file', file);
  form.set('kind', kind);
  return send<Food>(`/foods/${id}/photos`, form);
}

/** Read a label with the AI (nothing saved). */
export function readLabel(file: File) {
  const form = new FormData();
  form.set('file', file);
  return send<LabelReading>('/foods/read-label', form);
}
