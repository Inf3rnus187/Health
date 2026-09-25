import type { Food } from '../../api/foods';
import { useRefreshFood, useRefreshFoods } from '../../hooks/useFoods';
import { changedText } from './productText';

/** « ↻ Open Food Facts »: read the sheet's page again, by its barcode. */
export function RefreshFood(props: {
  food: Food;
  onDone: (note: string) => void;
}) {
  const refresh = useRefreshFood();
  if (!props.food.barcode) return null;
  const go = () =>
    refresh.mutate(props.food.id, {
      onSuccess: (r) => props.onDone(changedText(r.changed)),
      onError: (e) => props.onDone(e.message),
    });
  return (
    <button
      className="btn ghost"
      title={`Relire la page Open Food Facts du code ${props.food.barcode}`}
      disabled={refresh.isPending}
      onClick={go}
    >
      {refresh.isPending ? 'Lecture…' : '↻ Open Food Facts'}
    </button>
  );
}

function summary(r: ReturnType<typeof useRefreshFoods>['data']): string {
  if (!r) return '';
  const parts = [
    `${r.updated.length} mise(s) à jour`,
    `${r.unchanged} inchangée(s)`,
    r.failed.length &&
      `échec : ${r.failed.map((f) => `${f.name} (${f.reason})`).join(', ')}`,
    r.remaining && `${r.remaining} restante(s) : relancer`,
  ];
  return parts.filter(Boolean).join(' · ');
}

/** « ↻ Tout relire » : every sheet with a barcode, at once. */
export function RefreshAll({ foods }: { foods: Food[] }) {
  const refresh = useRefreshFoods();
  if (!foods.some((f) => f.barcode)) return null;
  return (
    <>
      <button
        className="btn ghost"
        disabled={refresh.isPending}
        onClick={() => refresh.mutate()}
      >
        {refresh.isPending ? 'Lecture…' : '↻ Tout relire sur Open Food Facts'}
      </button>
      {refresh.isSuccess && (
        <p className="muted small">{summary(refresh.data)}</p>
      )}
      {refresh.isError && <p className="error">{refresh.error.message}</p>}
    </>
  );
}
