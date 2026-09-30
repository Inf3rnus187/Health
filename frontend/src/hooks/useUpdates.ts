import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { fetchUpdate, installedBuild, requestUpdate } from '../api/system';
import { hub, ms } from '../settings';

/** Whether a newer build than this page was installed on the server
 * (looked for every ``update_check_s``, on focus, every
 * ``update_look_s`` while ``updating``). */
export function useNewBuild(updating = false): boolean {
  const [newer, setNewer] = useState(false);
  useEffect(() => {
    const look = () =>
      void installedBuild().then((build) => {
        if (build && build !== __BUILD_ID__) setNewer(true);
      });
    look();
    const every = updating ? hub().update_look_s : hub().update_check_s;
    const timer = setInterval(look, ms(every));
    window.addEventListener('focus', look);
    return () => {
      clearInterval(timer);
      window.removeEventListener('focus', look);
    };
  }, [updating]);
  return newer;
}

/** Changes waiting, and the update running (polled faster then);
 * the administrator's only (``enabled``). */
export function useUpdateState(enabled = true) {
  return useQuery({
    queryKey: ['system-update'],
    queryFn: fetchUpdate,
    enabled,
    retry: false,
    refetchInterval: (q) =>
      ['requested', 'running'].includes(q.state.data?.state ?? '')
        ? ms(hub().update_state_s)
        : ms(hub().update_check_s),
  });
}

export function useRequestUpdate() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: requestUpdate,
    onSuccess: (data) => client.setQueryData(['system-update'], data),
  });
}
