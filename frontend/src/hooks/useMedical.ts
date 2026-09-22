import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  analyzeAllMedicalDocs,
  analyzeMedicalDoc,
  deleteMedicalDoc,
  listMedicalDocs,
  uploadMedicalDoc,
} from '../api/medical';
import type { MedicalDoc } from '../api/types';

const POLL_MS = 5000;

function pending(docs: MedicalDoc[] | undefined): boolean {
  return (docs ?? []).some((doc) => doc.analysis_status === 'queued');
}

/** Documents; polls while an AI reading is queued so results appear. */
export function useMedicalDocs() {
  const client = useQueryClient();
  return useQuery({
    queryKey: ['medical'],
    queryFn: async () => {
      const docs = await listMedicalDocs();
      // New values may feed the markers once a reading completes.
      void client.invalidateQueries({ queryKey: ['evolution-markers'] });
      return docs;
    },
    refetchInterval: (query) => (pending(query.state.data) ? POLL_MS : false),
  });
}

export function useAnalyzeDoc() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => analyzeMedicalDoc(id),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['medical'] }),
  });
}

export function useAnalyzeAllDocs() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: analyzeAllMedicalDocs,
    onSuccess: () => void client.invalidateQueries({ queryKey: ['medical'] }),
  });
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
