import { useState } from 'react';

import { useMetricIndex } from '../hooks/useMetricIndex';
import { useSamples } from '../hooks/useSamples';
import { Pager } from './Pager';
import type { SampleFilters } from './SamplesFilters';
import { SamplesFilters } from './SamplesFilters';
import { SamplesTable } from './SamplesTable';

const LIMIT = 50;
const EMPTY: SampleFilters = { metricKey: '', start: '', end: '' };

export function SamplesBrowser() {
  const [filters, setFilters] = useState<SampleFilters>(EMPTY);
  const [offset, setOffset] = useState(0);
  const metrics = useMetricIndex();
  const query = useSamples({ ...filters, limit: LIMIT, offset });
  const patch = (change: Partial<SampleFilters>) => {
    setFilters({ ...filters, ...change });
    setOffset(0);
  };
  const page = query.data;
  return (
    <section className="card">
      <h2>Données brutes ({page?.total ?? 0})</h2>
      <SamplesFilters filters={filters} onChange={patch} />
      <SamplesTable rows={page?.items ?? []} metrics={metrics} />
      <Pager
        offset={offset}
        limit={LIMIT}
        total={page?.total ?? 0}
        onPage={setOffset}
      />
    </section>
  );
}
