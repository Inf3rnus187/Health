import type { Observation } from '../api/types';
import { shortDateTime } from '../utils/datetime';

function display(obs: Observation): string {
  if (obs.value_num !== null) {
    return `${obs.value_num} ${obs.unit ?? ''}`.trim();
  }
  return obs.value_text ?? '—';
}

export function ObservationRow({ obs }: { obs: Observation }) {
  return (
    <tr>
      <td>{shortDateTime(obs.effective_at)}</td>
      <td className="metric-key">{obs.label}</td>
      <td>{display(obs)}</td>
    </tr>
  );
}
