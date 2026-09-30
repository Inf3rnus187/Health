// The hub's settings the page follows: its timings (seconds) and the
// limits its forms show. Read once from GET /system/settings before
// the page is drawn; the values below are only the fallback when the
// hub does not answer (they equal the hub's defaults).

export interface HubSettings {
  retry_s: number;
  renew_every_s: number;
  refresh_timeout_s: number;
  update_check_s: number;
  update_look_s: number;
  update_state_s: number;
  update_recent_s: number;
  poll_s: number;
  reconcile_refresh_s: number;
  reconcile_refresh_steps: number;
  reanalysis_refresh_s: number;
  reanalysis_refresh_steps: number;
  photo_refresh_s: number[];
  reload_guard_s: number;
  page_sizes: number[];
  meal_photos: number;
  meal_analysis_max_delay_min: number;
  work_max_week_hours: number;
}

const FALLBACK: HubSettings = {
  retry_s: 5,
  renew_every_s: 720,
  refresh_timeout_s: 15,
  update_check_s: 300,
  update_look_s: 20,
  update_state_s: 15,
  update_recent_s: 1800,
  poll_s: 5,
  reconcile_refresh_s: 10,
  reconcile_refresh_steps: 18,
  reanalysis_refresh_s: 10,
  reanalysis_refresh_steps: 12,
  photo_refresh_s: [1.5, 4, 8, 13],
  reload_guard_s: 60,
  page_sizes: [10, 25, 50, 100, 200],
  meal_photos: 7,
  meal_analysis_max_delay_min: 60,
  work_max_week_hours: 48,
};

/** The page is drawn with the fallback if the hub has not answered in
 * this time (restarting): the only wait that cannot come from it. */
const WAIT_MS = 3000;

let current = FALLBACK;

/** The settings in force. */
export function hub(): HubSettings {
  return current;
}

/** Seconds → milliseconds. */
export const ms = (seconds: number): number => seconds * 1000;

/** Ask the hub once (before the first draw). */
export async function loadHubSettings(): Promise<void> {
  try {
    const res = await fetch('/api/v1/system/settings', {
      signal: AbortSignal.timeout(WAIT_MS),
    });
    if (res.ok) {
      current = { ...FALLBACK, ...((await res.json()) as HubSettings) };
    }
  } catch {
    // the hub is restarting: the fallback, as before
  }
}
