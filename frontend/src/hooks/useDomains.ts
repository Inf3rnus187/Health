import { useQuery } from '@tanstack/react-query';

import { fetchMetrics } from '../api/metrics';

const PREFERRED = ['body', 'sleep', 'ppc', 'workout', 'walk', 'habit', 'state'];

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
