import { useEffect, useState } from 'react';

import { getAccessToken } from '../api/client';

function fetchBlob(path: string): Promise<Blob> {
  const token = getAccessToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
  return fetch(`/api/v1${path}`, { headers }).then((res) =>
    res.ok ? res.blob() : Promise.reject(res.status),
  );
}

/** A private file (``/api/v1`` path) as a local URL, freed when done. */
export function useFileUrl(path: string | null): {
  url: string | null;
  error: string;
} {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!path) return undefined;
    let made: string | null = null;
    let active = true;
    fetchBlob(path)
      .then((blob) => {
        made = URL.createObjectURL(blob);
        if (active) setUrl(made);
      })
      .catch((status) => active && setError(`Fichier illisible (${status})`));
    return () => {
      active = false;
      if (made) URL.revokeObjectURL(made);
    };
  }, [path]);
  return { url, error };
}
