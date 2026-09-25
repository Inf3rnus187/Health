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

/** What Open Food Facts says beyond the 8 values (kept on the sheet). */
export interface ProductInfo {
  ingredients: string;
  allergens: string[];
  traces: string[];
  additives: string[];
  nutriscore: string;
  nutriscore_score: number | null;
  /** 1 unprocessed … 4 ultra-processed. */
  nova: number | null;
  fruits_veg_pct: number | null;
  /** fat, saturated-fat, sugars, salt → low, moderate, high. */
  levels: Record<string, string>;
  labels: string;
  categories: string;
  serving: string;
  /** Other nutrients, grams per 100 g. */
  other_100g: Record<string, number>;
  url: string;
}

export interface FoodIn {
  name: string;
  brand: string;
  aliases: string;
  package_g: number | null;
  /** How it is counted: « tomate », « tranche » (unit_g grams each). */
  unit_name: string;
  unit_g: number | null;
  /** What is usually eaten of it (g): the small box, ¼ of the big one. */
  portion_g: number | null;
  per_100g: Per100g;
  note: string;
  /** Where the values come from (étiquette, Ciqual, Open Food Facts). */
  source: string;
  barcode: string;
  product_info?: ProductInfo | null;
}

export interface Food extends FoodIn {
  id: string;
  photos: { id: string; kind: PhotoKind }[];
  created_at: string;
}

/** What the AI read on a label (or Open Food Facts): a proposal. */
export interface LabelReading {
  name: string;
  brand: string;
  package_g: number | null;
  per_100g: Per100g;
  barcode?: string;
  source?: string;
  product_info?: ProductInfo | null;
}

/** A food of the ANSES Ciqual table (values per 100 g, null: unknown). */
export interface CiqualRef {
  code: string;
  name: string;
  group: string;
  per_100g: Record<keyof Per100g, number | null>;
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

export const searchCiqual = (q: string) =>
  api<{ version: string; items: CiqualRef[] }>(
    `/ciqual?q=${encodeURIComponent(q)}&limit=12`,
  );
export const lookupBarcode = (code: string) =>
  api<LabelReading>(`/openfoodfacts/${encodeURIComponent(code)}`);

/** A barcode read on a photo: my food with that code, or the product. */
export interface ScanResult {
  barcodes: string[];
  food: Food | null;
  product: LabelReading | null;
  /** Whether the hub may look a product up on Open Food Facts. */
  online: boolean;
  note: string;
}

/** Read a pack's barcode on a photo (camera or gallery), on the hub. */
export function scanBarcode(file: File) {
  const form = new FormData();
  form.set('file', file);
  return send<ScanResult>('/foods/scan', form);
}

/** Read a label with the AI (nothing saved). */
export function readLabel(file: File) {
  const form = new FormData();
  form.set('file', file);
  return send<LabelReading>('/foods/read-label', form);
}
