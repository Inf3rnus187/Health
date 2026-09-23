import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { fetchUpdate, installedBuild, requestUpdate } from '../api/system';

const EVERY = 5 * 60 * 1000;

/** Whether a newer build than this page was installed on the server. */
export function useNewBuild(): boolean {
  const [newer, setNewer] = useState(false);
  useEffect(() => {
    const look = () =>
      void installedBuild().then((build) => {
        if (build && build !== __BUILD_ID__) setNewer(true);
      });
    look();
    const timer = setInterval(look, EVERY);
    window.addEventListener('focus', look);
    return () => {
      clearInterval(timer);
      window.removeEventListener('focus', look);
    };
  }, []);
  return newer;
}

/** Changes waiting, and the update running (polled faster then). */
export function useUpdateState() {
  return useQuery({
    queryKey: ['system-update'],
    queryFn: fetchUpdate,
    retry: false,
    refetchInterval: (q) =>
      ['requested', 'running'].includes(q.state.data?.state ?? '')
        ? 15_000
        : EVERY,
  });
}

export function useRequestUpdate() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: requestUpdate,
    onSuccess: (data) => client.setQueryData(['system-update'], data),
  });
}
