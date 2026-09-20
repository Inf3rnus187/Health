import { useState } from 'react';

import { useEcg } from '../hooks/useRecords';
import { EcgRow } from './EcgRow';
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
      <div className="table-wrap scroll-y">
        <table className="data-table">
          <tbody>
            {rows.map((row) => (
              <EcgRow key={row.id} row={row} onView={setSelected} />
            ))}
          </tbody>
        </table>
      </div>
      {selected && (
        <EcgViewer id={selected} onClose={() => setSelected(null)} />
      )}
    </section>
  );
}
