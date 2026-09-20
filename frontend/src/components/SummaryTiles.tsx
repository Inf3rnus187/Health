import { useSummary } from '../hooks/useSummary';
import { SummaryTile } from './SummaryTile';

export function SummaryTiles() {
  const tiles = useSummary().data ?? [];
  if (tiles.length === 0) {
    return (
      <p className="muted">
        Aucune donnée récente — importez vos données ou ajoutez une mesure.
      </p>
    );
  }
  return (
    <div className="tiles">
      {tiles.map((tile) => (
        <SummaryTile key={tile.key} tile={tile} />
      ))}
    </div>
  );
}
