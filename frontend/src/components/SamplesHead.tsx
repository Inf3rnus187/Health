import { PageSize } from './PageSize';

interface SamplesHeadProps {
  total: number;
  limit: number;
  onResize: (size: number) => void;
}

export function SamplesHead({ total, limit, onResize }: SamplesHeadProps) {
  return (
    <div className="data-head">
      <h2>Données brutes ({total})</h2>
      <PageSize value={limit} onChange={onResize} />
    </div>
  );
}
