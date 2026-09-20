// Semantic colour palette (§10.1): the same metric/domain always maps to
// the same colour, everywhere. Per-metric overrides win over the domain.

const DEFAULT = '#64748b';

const domainColor: Record<string, string> = {
  body: '#2563eb',
  sleep: '#7c3aed',
  nap: '#8b5cf6',
  ppc: '#0891b2',
  rest: '#059669',
  symptom: '#e11d48',
  workout: '#dc2626',
  walk: '#16a34a',
  med: '#9333ea',
  habit: '#d97706',
  water: '#0ea5e9',
  hydration: '#0284c7',
  food: '#ca8a04',
  state: '#db2777',
  photo: '#475569',
  ai: '#7c3aed',
  context: '#64748b',
  activity: '#16a34a',
  heart: '#dc2626',
  fitness: '#ea580c',
  vitals: '#0891b2',
  nutrition: '#ca8a04',
  apple: '#64748b',
};

const metricColor: Record<string, string> = {
  'body.weight': '#2563eb',
  'sleep.spo2_min': '#0891b2',
  'sleep.spo2_avg': '#22d3ee',
  'ppc.ahi': '#f59e0b',
};

export function colorForMetric(key: string): string {
  const exact = metricColor[key];
  if (exact) return exact;
  const domain = key.split('.')[0] ?? '';
  return domainColor[domain] ?? DEFAULT;
}
