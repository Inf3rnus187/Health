interface DataToolbarProps {
  total: number;
  selected: number;
  onDelete: () => void;
}

export function DataToolbar({ total, selected, onDelete }: DataToolbarProps) {
  return (
    <div className="data-head">
      <h2>Données ({total})</h2>
      <button className="btn" disabled={selected === 0} onClick={onDelete}>
        Supprimer ({selected})
      </button>
    </div>
  );
}
