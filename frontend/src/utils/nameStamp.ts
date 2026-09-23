// A date-time written in a file name ("2026-05-09 03h47.pdf"): the
// same patterns as the hub reads (backend receipt_read.name_stamp).

const SEP = '[-_. ]';
const TSEP = '[-_. tT]*';
const CLOCK = `${TSEP}(\\d{1,2})[hH:._-](\\d{2})(?!\\d)`;
const NAMES: [RegExp, string][] = [
  [
    new RegExp(`(?<!\\d)(\\d{1,2})${SEP}(\\d{1,2})${SEP}(\\d{4})${CLOCK}`),
    'dmyhi',
  ],
  [
    new RegExp(`(?<!\\d)(\\d{4})${SEP}(\\d{1,2})${SEP}(\\d{1,2})${CLOCK}`),
    'ymdhi',
  ],
  [/(?<!\d)(\d{4})(\d{2})(\d{2})[-_tT ](\d{2})(\d{2})(?!\d)/, 'ymdhi'],
];

/** ``YYYY-MM-DDTHH:MM`` of real day / time parts, else null. */
function stampOf(p: Record<string, number>): string | null {
  const [y, m, d, h, i] = ['y', 'm', 'd', 'h', 'i'].map((k) => p[k] ?? -1);
  const at = new Date(Date.UTC(y ?? 0, (m ?? 0) - 1, d, h, i));
  const real =
    at.getUTCFullYear() === y &&
    at.getUTCMonth() + 1 === m &&
    at.getUTCDate() === d &&
    at.getUTCHours() === h &&
    at.getUTCMinutes() === i;
  return real ? at.toISOString().slice(0, 16) : null;
}

/** The ``YYYY-MM-DDTHH:MM`` a file name carries, else null. */
export function nameStamp(name: string): string | null {
  for (const [pattern, order] of NAMES) {
    const found = pattern.exec(name);
    if (!found) {
      continue;
    }
    const parts: Record<string, number> = {};
    [...order].forEach((key, n) => {
      parts[key] = Number(found[n + 1]);
    });
    const stamp = stampOf(parts);
    if (stamp) {
      return stamp;
    }
  }
  return null;
}
