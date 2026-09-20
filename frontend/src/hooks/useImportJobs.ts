import { useQuery } from '@tanstack/react-query';

import { listImportJobs } from '../api/imports';
import type { ImportJob } from '../api/types';

const ACTIVE = new Set(['queued', 'running']);

function interval(jobs: ImportJob[] | undefined): number | false {
  const busy = (jobs ?? []).some((job) => ACTIVE.has(job.status));
  return busy ? 1500 : false;
}

/** Poll the import-job list while any job is still running. */
export function useImportJobs() {
  return useQuery({
    queryKey: ['import-jobs'],
    queryFn: listImportJobs,
    refetchInterval: (query) => interval(query.state.data),
  });
}
