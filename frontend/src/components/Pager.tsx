interface PagerProps {
  offset: number;
  limit: number;
  total: number;
  onPage: (offset: number) => void;
}

export function Pager({ offset, limit, total, onPage }: PagerProps) {
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div className="pager">
      <button
        className="btn ghost"
        disabled={offset === 0}
        onClick={() => onPage(Math.max(0, offset - limit))}
      >
        Précédent
      </button>
      <span className="muted">
        {from}–{to} sur {total}
      </span>
      <button
        className="btn ghost"
        disabled={to >= total}
        onClick={() => onPage(offset + limit)}
      >
        Suivant
      </button>
    </div>
  );
}
