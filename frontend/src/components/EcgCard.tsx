import { useEcg } from '../hooks/useRecords';
import { EcgRow } from './EcgRow';

export function EcgCard() {
  const rows = useEcg().data ?? [];
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
              <EcgRow key={row.id} row={row} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
