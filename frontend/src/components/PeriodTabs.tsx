import type { Bucket } from '../api/types';

const OPTIONS: { key: Bucket; label: string }[] = [
  { key: 'day', label: 'Jour' },
  { key: 'week', label: 'Semaine' },
  { key: 'month', label: 'Mois' },
  { key: 'year', label: 'Année' },
];

interface PeriodTabsProps {
  bucket: Bucket;
  onBucket: (bucket: Bucket) => void;
  onReset: () => void;
}

export function PeriodTabs({ bucket, onBucket, onReset }: PeriodTabsProps) {
  return (
    <div className="tabs">
      {OPTIONS.map((option) => (
        <button
          key={option.key}
          className={option.key === bucket ? 'tab active' : 'tab'}
          onClick={() => onBucket(option.key)}
        >
          {option.label}
        </button>
      ))}
      <button className="tab" onClick={onReset}>
        Tout (réinit. zoom)
      </button>
    </div>
  );
}
