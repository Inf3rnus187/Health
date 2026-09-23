import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { type Bulk, deleteMany } from '../api/bulk';
import { FED } from './useWork';

/** Meals and the medical views (appointments are on the timeline). */
const CARE = ['meals', 'appointments', 'record', 'care-overview'];

/** Items ticked in a list, to act on at once. */
export interface Selection {
  has: (id: string) => boolean;
  toggle: (id: string) => void;
  set: (ids: string[]) => void;
}

export function useSelection(): Selection {
  const [ids, setIds] = useState<Set<string>>(() => new Set());
  const toggle = (id: string) =>
    setIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  return { has: (id) => ids.has(id), toggle, set: (l) => setIds(new Set(l)) };
}

/** Delete many items, then refresh every view they feed. */
export function useBulkDelete(what: Bulk) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (a: { ids: string[]; meals: boolean }) =>
      deleteMany(what, a.ids, a.meals),
    onSuccess: () => {
      for (const name of [...CARE, ...FED]) {
        void client.invalidateQueries({ queryKey: [name] });
      }
    },
  });
}
