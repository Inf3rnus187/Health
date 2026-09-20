import type { Trend, TrendPoint } from '../api/types';

/** Convert a trend's date/value points into epoch-ms points for the
 *  numeric time axis. */
export function toPoints(trend: Trend | undefined): TrendPoint[] {
  return (trend?.points ?? []).map((point) => ({
    t: Date.parse(point.date_key),
    value: point.value,
  }));
}
