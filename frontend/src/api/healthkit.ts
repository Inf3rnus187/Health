import { api } from './client';

/** What the hub holds from the iPhone app (POST /sync/healthkit). */
export interface HealthKitStatus {
  last_sync_at: string | null;
  samples: number;
  workouts: number;
  metrics: { key: string; label: string; samples: number; last: string }[];
}

export const fetchHealthKitStatus = () =>
  api<HealthKitStatus>('/sync/healthkit');
