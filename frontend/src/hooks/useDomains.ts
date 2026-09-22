import { useQuery } from '@tanstack/react-query';

import { fetchDomainLabels, fetchMetrics } from '../api/metrics';

const PREFERRED = [
  'body',
  'heart',
  'vitals',
  'bio',
  'activity',
  'sleep',
  'ppc',
  'habit',
  'symptom',
];

function ordered(domains: Set<string>): string[] {
  const known = PREFERRED.filter((d) => domains.has(d));
  const extra = [...domains].filter((d) => !PREFERRED.includes(d)).sort();
  return [...known, ...extra];
}

/** Distinct metric domains, preferred ones first, then imported extras. */
export function useDomains(): string[] {
  const { data } = useQuery({ queryKey: ['metrics'], queryFn: fetchMetrics });
  const domains = new Set<string>();
  for (const metric of data ?? []) {
    domains.add(metric.domain);
  }
  const result = ordered(domains);
  return result.length > 0 ? result : PREFERRED;
}

/** Domain code → French name (the code itself while loading / unknown). */
export function useDomainLabel(): (domain: string) => string {
  const { data } = useQuery({
    queryKey: ['domain-labels'],
    queryFn: fetchDomainLabels,
    staleTime: Infinity,
  });
  return (domain) => data?.[domain] ?? domain;
}
