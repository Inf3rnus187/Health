import { useState } from 'react';

import { useClinicalDoc, useObservations } from '../hooks/useClinical';
import { ClinicalHead } from './ClinicalHead';
import { ClinicalTable } from './ClinicalTable';
import { Pager } from './Pager';
import { SearchBox } from './SearchBox';

const LIMIT = 10;

export function ClinicalCard() {
  const [search, setSearch] = useState('');
  const [offset, setOffset] = useState(0);
  const doc = useClinicalDoc().data;
  const page = useObservations(search, LIMIT, offset).data;
  if (!doc) return null;
  const onSearch = (value: string) => {
    setSearch(value);
    setOffset(0);
  };
  return (
    <section className="card">
      <ClinicalHead count={doc.observation_count} />
      <SearchBox value={search} onChange={onSearch} />
      <ClinicalTable rows={page?.items ?? []} />
      <Pager
        offset={offset}
        limit={LIMIT}
        total={page?.total ?? 0}
        onPage={setOffset}
      />
    </section>
  );
}
