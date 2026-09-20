import { useWorkouts } from '../hooks/useRecords';
import { WorkoutRow } from './WorkoutRow';

export function WorkoutsCard() {
  const rows = useWorkouts().data ?? [];
  if (rows.length === 0) {
    return null;
  }
  return (
    <section className="card">
      <h2>Séances ({rows.length})</h2>
      <div className="table-wrap scroll-y">
        <table className="data-table">
          <tbody>
            {rows.map((row) => (
              <WorkoutRow key={row.id} row={row} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
