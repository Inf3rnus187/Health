import type { Sample } from '../api/types';

interface SampleRowProps {
  sample: Sample;
  metricKey: string;
}

function display(sample: Sample): string {
  if (sample.value_num !== null) {
    return String(sample.value_num);
  }
  return sample.value_text ?? '';
}

export function SampleRow({ sample, metricKey }: SampleRowProps) {
  return (
    <tr>
      <td>{sample.start_at.replace('T', ' ').slice(0, 16)}</td>
      <td className="metric-key">{metricKey}</td>
      <td>{display(sample)}</td>
      <td className="metric-type">{sample.unit ?? ''}</td>
      <td className="metric-type">{sample.source}</td>
    </tr>
  );
}
