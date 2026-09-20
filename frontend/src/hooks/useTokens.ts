import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { createToken, listTokens, revokeToken } from '../api/tokens';

export function useTokens() {
  return useQuery({ queryKey: ['tokens'], queryFn: listTokens });
}

export function useCreateToken() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => createToken('iPhone – Raccourci', ['ingest:watch']),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['tokens'] }),
  });
}

export function useRevokeToken() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => revokeToken(id),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['tokens'] }),
  });
}
