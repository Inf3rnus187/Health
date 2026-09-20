import type { SummaryTile as Tile } from '../api/types';

function fmtValue(tile: Tile): string {
  if (tile.key.startsWith('sleep.') && tile.unit === 'min') {
    const total = Math.round(tile.value);
    const h = Math.floor(total / 60);
    const m = String(total % 60).padStart(2, '0');
    return `${h} h ${m}`;
  }
  const num = Number.isInteger(tile.value)
    ? String(tile.value)
    : tile.value.toFixed(1);
  return tile.unit ? `${num} ${tile.unit}` : num;
}

function timeOf(iso: string | null): string {
  if (!iso) {
    return '';
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return '';
  }
  const pad = (n: number) => String(n).padStart(2, '0');
  return ` · ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function SummaryTile({ tile }: { tile: Tile }) {
  return (
    <div className="tile">
      <span className="tile-label muted">{tile.label}</span>
      <span className="tile-value">{fmtValue(tile)}</span>
      <span className="tile-date muted">
        {tile.date_key}
        {timeOf(tile.at)}
      </span>
    </div>
  );
}
