import type { SummaryTile as Tile } from '../api/types';

function fmt(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

export function SummaryTile({ tile }: { tile: Tile }) {
  const unit = tile.unit ? ` ${tile.unit}` : '';
  return (
    <div className="tile">
      <span className="tile-label muted">{tile.label}</span>
      <span className="tile-value">
        {fmt(tile.value)}
        {unit}
      </span>
      <span className="tile-date muted">{tile.date_key}</span>
    </div>
  );
}
