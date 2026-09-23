import { useWorkouts } from '../hooks/useRecords';
import { PagedRows } from './PagedRows';
import { WorkoutRow } from './WorkoutRow';

export function WorkoutsCard() {
  const rows = useWorkouts().data ?? [];
  if (rows.length === 0) {
    return null;
  }
  return (
    <section className="card">
      <h2>Séances ({rows.length})</h2>
      <PagedRows
        items={rows}
        row={(row) => <WorkoutRow key={row.id} row={row} />}
      />
    </section>
  );
}
