import { api } from './client';

/** What can be deleted many at once. */
export type Bulk =
  'evidence' | 'work/sessions' | 'absences' | 'meals' | 'appointments';

export interface Deleted {
  deleted: number;
  meals: number;
}

/** Delete many items (only the user's own go); proofs: meals too. */
export const deleteMany = (what: Bulk, ids: string[], meals = false) =>
  api<Deleted>(`/${what}/delete`, {
    method: 'POST',
    body: JSON.stringify(what === 'evidence' ? { ids, meals } : { ids }),
  });
