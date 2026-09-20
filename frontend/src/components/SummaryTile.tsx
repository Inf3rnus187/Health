import type { SummaryTile as Tile } from '../api/types';
import { colorForMetric } from '../theme/palette';
import { Sparkline } from './Sparkline';

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

function Evolution({ delta }: { delta: number | null }) {
  if (delta === null || delta === 0) {
    return null;
  }
  return (
    <span className="delta muted">
      {delta > 0 ? '▲' : '▼'} {Math.abs(delta)}
    </span>
  );
}

export function SummaryTile({ tile }: { tile: Tile }) {
  const avg = tile.avg7 !== null ? ` · moy7 ${tile.avg7}` : '';
  return (
    <div className="tile">
      <span className="tile-label muted">{tile.label}</span>
      <span className="tile-value">
        {fmtValue(tile)}
        <Evolution delta={tile.delta} />
      </span>
      <Sparkline values={tile.spark} color={colorForMetric(tile.key)} />
      <span className="tile-date muted">
        {tile.date_key}
        {timeOf(tile.at)}
        {avg}
      </span>
    </div>
  );
}
