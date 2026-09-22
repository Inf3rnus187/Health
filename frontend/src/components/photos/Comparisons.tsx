import type { PhotoComparison } from '../../api/photos';
import { shortDate, signed } from '../../utils/format';

// Paired-comparison deltas live in [-2, 2]; negative means less visible
// abdominal fat than the reference photo (an improvement).
type Tone = 'good' | 'bad' | 'same';

const SAME_BELOW = 0.25;

const ARROW: Record<Tone, string> = { good: '▼', bad: '▲', same: '≈' };

const TEXT: Record<Tone, string> = {
  good: 'moins de graisse visible',
  bad: 'plus de graisse visible',
  same: 'identique',
};

function toneOf(delta: number): Tone {
  if (Math.abs(delta) < SAME_BELOW) {
    return 'same';
  }
  return delta < 0 ? 'good' : 'bad';
}

function DeltaText({ delta }: { delta: number }) {
  const tone = toneOf(delta);
  const text =
    tone === 'same'
      ? `${ARROW.same} ${TEXT.same}`
      : `${ARROW[tone]} ${signed(delta)} · ${TEXT[tone]}`;
  return <span className={`delta-${tone}`}>{text}</span>;
}

interface DeltaRowProps {
  label: string;
  delta: number;
  reliable: boolean;
}

function DeltaRow({ label, delta, reliable }: DeltaRowProps) {
  return (
    <li>
      <span className="cmp-label">{label}</span>
      <DeltaText delta={delta} />
      {!reliable && <span className="muted"> (peu fiable)</span>}
    </li>
  );
}

function numericDeltas(item: PhotoComparison): [string, number][] {
  return Object.entries(item.deltas ?? {}).filter(
    (entry): entry is [string, number] => typeof entry[1] === 'number',
  );
}

interface ItemProps {
  item: PhotoComparison;
  labels: Record<string, string>;
}

function ComparisonItem({ item, labels }: ItemProps) {
  return (
    <li className="cmp">
      <div className="cmp-head">
        <strong>{item.label || item.horizon}</strong>
        {item.ref_date && (
          <span className="muted">{shortDate(item.ref_date)}</span>
        )}
      </div>
      <ul className="cmp-deltas">
        {numericDeltas(item).map(([key, delta]) => (
          <DeltaRow
            key={key}
            label={labels[key] ?? key}
            delta={delta}
            reliable={item.consistent?.[key] !== false}
          />
        ))}
      </ul>
    </li>
  );
}

export function Comparisons({
  items,
  labels,
}: {
  items: PhotoComparison[];
  labels: Record<string, string>;
}) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="cmp-block">
      <span className="analysis-title">Comparaisons appariées</span>
      <ul className="cmp-list">
        {items.map((item) => (
          <ComparisonItem key={item.horizon} item={item} labels={labels} />
        ))}
      </ul>
    </div>
  );
}
