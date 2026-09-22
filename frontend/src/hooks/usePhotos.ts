import { useQuery } from '@tanstack/react-query';

import { fetchAnalysis, listPhotos } from '../api/photos';

export function usePhotos(angle?: string) {
  return useQuery({
    queryKey: ['photos', angle ?? 'all'],
    queryFn: () => listPhotos(angle),
  });
}

export function usePhotoAnalysis(id: string) {
  return useQuery({
    queryKey: ['photo-analysis', id],
    queryFn: () => fetchAnalysis(id),
    retry: false,
  });
}
