import type { Measurement } from '../api/types';

interface DataRowProps {
  row: Measurement;
  metricKey: string;
  checked: boolean;
  onToggle: (id: string) => void;
}

export function DataRow({ row, metricKey, checked, onToggle }: DataRowProps) {
  return (
    <tr>
      <td>
        <input
          type="checkbox"
          checked={checked}
          onChange={() => onToggle(row.id)}
        />
      </td>
      <td>{row.date_key}</td>
      <td className="metric-key">{metricKey}</td>
      <td>{String(row.value)}</td>
      <td className="metric-type">{row.source}</td>
    </tr>
  );
}
