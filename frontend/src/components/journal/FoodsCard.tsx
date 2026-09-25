import { useState } from 'react';

import type { Food } from '../../api/foods';
import type { StockLevel } from '../../api/stock';
import { useDeleteFood, useFoods } from '../../hooks/useFoods';
import { useStock } from '../../hooks/useStock';
import { frNumber } from '../../utils/format';
import { FoodForm } from './FoodForm';
import { productSummary } from './productText';
import { bySize, portionText } from './foodLabel';
import { StockPanel } from './StockPanel';
import { stockText } from './stockText';

/** « 150 kcal · P 3,5 · G 30 · L 1,8 » for 100 g. */
function per100(food: Food): string {
  const p = food.per_100g;
  const part = (label: string, value?: number) =>
    value == null ? null : `${label} ${frNumber(value, 1)}`;
  return [
    p.energy_kcal == null ? null : `${frNumber(p.energy_kcal, 0)} kcal`,
    part('prot.', p.protein_g),
    part('gluc.', p.carbs_g),
    part('lip.', p.fat_g),
  ]
    .filter(Boolean)
    .join(' · ');
}

/** « 185 g · 1 pavé = 100 g · portion : tout (185 g) · 83 kcal… ». */
function facts(food: Food): string {
  const unit = food.unit_name || 'unité';
  return [
    food.package_g != null && `${frNumber(food.package_g, 0)} g`,
    food.unit_g != null && `1 ${unit} = ${frNumber(food.unit_g, 0)} g`,
    food.portion_g != null && portionText(food),
    `${per100(food) || 'valeurs à compléter'} (100 g)`,
    food.photos.length > 0 && `${food.photos.length} photo(s)`,
    food.source && food.source.split(' · ')[0],
  ]
    .filter(Boolean)
    .join(' · ');
}

function Summary({ food, level }: { food: Food; level?: StockLevel }) {
  const about = food.product_info ? productSummary(food.product_info) : '';
  return (
    <div>
      <strong>{food.name}</strong>
      {food.brand && <span className="muted"> · {food.brand}</span>}
      <div className="muted small">{facts(food)}</div>
      {about && <div className="muted small">{about}</div>}
      {level && <div className="small">Stock : {stockText(level)}</div>}
    </div>
  );
}

function useDelete(food: Food) {
  const del = useDeleteFood();
  return () => {
    if (window.confirm(`Supprimer « ${food.name} » et ses photos ?`)) {
      del.mutate(food.id);
    }
  };
}

function Row(props: { food: Food; level?: StockLevel; onEdit: () => void }) {
  const onDelete = useDelete(props.food);
  const [stock, setStock] = useState(false);
  const { food } = props;
  return (
    <li className="food-row">
      <Summary food={food} level={props.level} />
      <div className="row-actions">
        <button className="btn ghost" onClick={() => setStock(!stock)}>
          Stock
        </button>
        <button className="btn ghost" onClick={props.onEdit}>
          Modifier
        </button>
        <button className="btn ghost" onClick={onDelete}>
          Supprimer
        </button>
      </div>
      {stock && <StockPanel food={food} />}
    </li>
  );
}

const ABOUT =
  'Une fiche par aliment courant (sachet, tomate, comté…), remplie une ' +
  'fois : valeurs pour 100 g et poids d’une unité. Un repas qui le nomme ' +
  'est calculé avec : mêmes chiffres à chaque fois.';

/** The sheet being edited: a new one, or one of the list (kept fresh). */
function Editor(props: {
  editing: string | null;
  foods: Food[];
  onEdit: (id: string | null) => void;
}) {
  const { editing, onEdit } = props;
  if (editing === null) {
    return (
      <button className="btn" onClick={() => onEdit('new')}>
        + Ajouter un aliment
      </button>
    );
  }
  const food = props.foods.find((f) => f.id === editing) ?? null;
  return <FoodForm key={editing} food={food} onDone={() => onEdit(null)} />;
}

/** The user's usual foods: a list, and the sheet being edited. */
export function FoodsCard() {
  const foods = useFoods().data ?? [];
  const levels = useStock().data?.foods ?? [];
  const [editing, setEditing] = useState<string | null>(null);
  return (
    <section className="card">
      <h2>Mes aliments ({foods.length})</h2>
      <p className="muted">{ABOUT}</p>
      <Editor editing={editing} foods={foods} onEdit={setEditing} />
      <ul className="food-list">
        {[...foods].sort(bySize).map((food) => (
          <Row
            key={food.id}
            food={food}
            level={levels.find((lv) => lv.food_id === food.id)}
            onEdit={() => setEditing(food.id)}
          />
        ))}
      </ul>
    </section>
  );
}
