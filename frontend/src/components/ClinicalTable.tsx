import type { Observation } from '../api/types';
import { ObservationRow } from './ObservationRow';

export function ClinicalTable({ rows }: { rows: Observation[] }) {
  if (rows.length === 0) {
    return <p className="muted">Aucune observation.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="data-table">
        <tbody>
          {rows.map((obs) => (
            <ObservationRow key={obs.id} obs={obs} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
