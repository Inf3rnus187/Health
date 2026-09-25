import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addStock,
  deleteStockMove,
  fetchStock,
  fetchStockHistory,
} from '../api/stock';

export const useStock = () =>
  useQuery({ queryKey: ['stock'], queryFn: fetchStock });

export const useStockHistory = (foodId: string) =>
  useQuery({
    queryKey: ['stock', foodId],
    queryFn: () => fetchStockHistory(foodId),
  });

function useStockAction<A, R>(fn: (arg: A) => Promise<R>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => client.invalidateQueries({ queryKey: ['stock'] }),
  });
}

export const useAddStock = () => useStockAction(addStock);
export const useDeleteStockMove = () => useStockAction(deleteStockMove);
