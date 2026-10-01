import { api } from './client';

/** One kind of line the hub refused: its type, why, how many, when. */
export interface RefusedKind {
  type: string;
  reason: string;
  count: number;
  last: string;
}

/** Lines refused over the last `days` (`checked`: syncs that say so). */
export interface RefusedLines {
  days: number;
  syncs: number;
  checked: number;
  lines: number;
  kinds: RefusedKind[];
}

/** What the hub holds from the iPhone app (POST /sync/healthkit). */
export interface HealthKitStatus {
  last_sync_at: string | null;
  samples: number;
  workouts: number;
  metrics: { key: string; label: string; samples: number; last: string }[];
  refused: RefusedLines;
}

export const fetchHealthKitStatus = () =>
  api<HealthKitStatus>('/sync/healthkit');
