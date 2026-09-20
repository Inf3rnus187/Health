import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  deleteMedicalDoc,
  listMedicalDocs,
  uploadMedicalDoc,
} from '../api/medical';

export function useMedicalDocs() {
  return useQuery({ queryKey: ['medical'], queryFn: listMedicalDocs });
}

export function useUploadDoc() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (form: FormData) => uploadMedicalDoc(form),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['medical'] }),
  });
}

export function useDeleteDoc() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteMedicalDoc(id),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['medical'] }),
  });
}
