import { useState } from 'react';

import { useEcg } from '../hooks/useRecords';
import { EcgRow } from './EcgRow';
import { PagedRows } from './PagedRows';
import { EcgViewer } from './EcgViewer';

export function EcgCard() {
  const rows = useEcg().data ?? [];
  const [selected, setSelected] = useState<string | null>(null);
  if (rows.length === 0) {
    return null;
  }
  return (
    <section className="card">
      <h2>Électrocardiogrammes ({rows.length})</h2>
      <PagedRows
        items={rows}
        row={(row) => <EcgRow key={row.id} row={row} onView={setSelected} />}
      />
      {selected && (
        <EcgViewer id={selected} onClose={() => setSelected(null)} />
      )}
    </section>
  );
}
