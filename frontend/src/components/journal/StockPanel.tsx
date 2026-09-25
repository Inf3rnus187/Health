import { useState } from 'react';

import type { Food } from '../../api/foods';
import type { StockKind } from '../../api/stock';
import { useAddStock } from '../../hooks/useStock';
import { num } from './foodDraft';
import { StockHistory } from './StockHistory';
import { type Measure, measures } from './stockText';

const ACTIONS: [StockKind, string][] = [
  ['purchase', 'J’ai acheté'],
  ['count', 'Il m’en reste'],
  ['out', 'Jeté / donné'],
];

function useStockForm(food: Food) {
  const options = measures(food);
  const [qty, setQty] = useState('1');
  const [measure, setMeasure] = useState<Measure>(options[0]?.[0] ?? 'grams');
  const add = useAddStock();
  const send = (kind: StockKind) => {
    const value = num(qty);
    if (value == null) return;
    add.mutate({ food_id: food.id, kind, [measure]: value });
  };
  return { options, qty, setQty, measure, setMeasure, add, send };
}

function Quantity({ s }: { s: ReturnType<typeof useStockForm> }) {
  return (
    <div className="quick">
      <input
        className="input stock-qty"
        inputMode="decimal"
        value={s.qty}
        onChange={(e) => s.setQty(e.target.value)}
      />
      <select
        className="input"
        value={s.measure}
        onChange={(e) => s.setMeasure(e.target.value as Measure)}
      >
        {s.options.map(([key, label]) => (
          <option key={key} value={key}>
            {label}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Bought, left, thrown: the stock of one food, and its history. */
export function StockPanel({ food }: { food: Food }) {
  const s = useStockForm(food);
  return (
    <div className="stock-panel">
      <Quantity s={s} />
      <div className="quick">
        {ACTIONS.map(([kind, label]) => (
          <button
            key={kind}
            type="button"
            className="btn ghost"
            disabled={s.add.isPending}
            onClick={() => s.send(kind)}
          >
            {label}
          </button>
        ))}
      </div>
      {s.add.isError && <p className="error">{s.add.error.message}</p>}
      <StockHistory foodId={food.id} />
    </div>
  );
}
