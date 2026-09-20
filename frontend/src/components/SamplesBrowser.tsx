import { useState } from 'react';

import { useMetricIndex } from '../hooks/useMetricIndex';
import { useSamples } from '../hooks/useSamples';
import { Pager } from './Pager';
import type { SampleFilters } from './SamplesFilters';
import { SamplesFilters } from './SamplesFilters';
import { SamplesHead } from './SamplesHead';
import { SamplesTable } from './SamplesTable';

const EMPTY: SampleFilters = { metricKey: '', start: '', end: '' };

export function SamplesBrowser() {
  const [filters, setFilters] = useState<SampleFilters>(EMPTY);
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(10);
  const metrics = useMetricIndex();
  const page = useSamples({ ...filters, limit, offset }).data;
  const patch = (change: Partial<SampleFilters>) => {
    setFilters({ ...filters, ...change });
    setOffset(0);
  };
  const resize = (size: number) => {
    setLimit(size);
    setOffset(0);
  };
  const total = page?.total ?? 0;
  return (
    <section className="card">
      <SamplesHead total={total} limit={limit} onResize={resize} />
      <SamplesFilters filters={filters} onChange={patch} />
      <SamplesTable rows={page?.items ?? []} metrics={metrics} />
      <Pager offset={offset} limit={limit} total={total} onPage={setOffset} />
    </section>
  );
}
