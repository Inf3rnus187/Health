import type { WorkoutRow as Row } from '../api/types';
import { shortDateTime } from '../utils/datetime';

function activity(type: string): string {
  return type.replace('HKWorkoutActivityType', '');
}

function num(value: number | null, digits = 0): string {
  return value === null ? '—' : value.toFixed(digits);
}

export function WorkoutRow({ row }: { row: Row }) {
  return (
    <tr>
      <td>{shortDateTime(row.start_at)}</td>
      <td className="metric-key">{activity(row.activity_type)}</td>
      <td>{num(row.duration_min)} min</td>
      <td>{num(row.energy_kcal)} kcal</td>
      <td>{num(row.distance_km, 2)} km</td>
    </tr>
  );
}
