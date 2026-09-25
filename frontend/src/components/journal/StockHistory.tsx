import type { StockHistory as History } from '../../api/stock';
import { useDeleteStockMove, useStockHistory } from '../../hooks/useStock';
import { frNumber } from '../../utils/format';
import { KINDS, when } from './stockText';

interface Line {
  key: string;
  at: string;
  text: string;
  moveId?: string;
}

const SHOWN = 8;

/** Moves and meals, newest first. */
function lines(h: History): Line[] {
  const moves = h.moves.map((m) => ({
    key: m.id,
    at: m.at,
    text: `${KINDS[m.kind]} · ${m.said || `${frNumber(m.grams, 1)} g`}`,
    moveId: m.id,
  }));
  const meals = h.eaten.map((e) => ({
    key: `${e.meal_id}-${e.eaten_at}`,
    at: e.eaten_at,
    text: `Mangé (repas) · ${frNumber(e.grams, 1)} g`,
  }));
  return [...moves, ...meals].sort((a, b) => b.at.localeCompare(a.at));
}

function Entry(props: { line: Line; onDrop: (id: string) => void }) {
  const { line } = props;
  return (
    <li>
      {when(line.at)} · {line.text}
      {line.moveId && (
        <button
          type="button"
          className="chip-x"
          title="Supprimer (erreur de saisie)"
          onClick={() => line.moveId && props.onDrop(line.moveId)}
        >
          ×
        </button>
      )}
    </li>
  );
}

/** The food's last moves and the meals that took from it. */
export function StockHistory({ foodId }: { foodId: string }) {
  const history = useStockHistory(foodId).data;
  const drop = useDeleteStockMove();
  if (!history) return null;
  const all = lines(history);
  return (
    <ul className="stock-history muted small">
      {all.slice(0, SHOWN).map((line) => (
        <Entry key={line.key} line={line} onDrop={(id) => drop.mutate(id)} />
      ))}
      {all.length > SHOWN && <li>… {all.length - SHOWN} de plus</li>}
    </ul>
  );
}
