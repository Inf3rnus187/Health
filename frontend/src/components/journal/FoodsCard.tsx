import { useState } from 'react';

import type { Food } from '../../api/foods';
import { useDeleteFood, useFoods } from '../../hooks/useFoods';
import { frNumber } from '../../utils/format';
import { FoodForm } from './FoodForm';

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

function Summary({ food }: { food: Food }) {
  return (
    <div>
      <strong>{food.name}</strong>
      {food.brand && <span className="muted"> · {food.brand}</span>}
      <div className="muted small">
        {food.package_g != null && `${frNumber(food.package_g, 0)} g · `}
        {food.unit_g != null &&
          `1 ${food.unit_name || 'unité'} = ${frNumber(food.unit_g, 0)} g · `}
        {per100(food) || 'valeurs à compléter'} (100 g)
        {food.photos.length > 0 && ` · ${food.photos.length} photo(s)`}
        {food.source && ` · ${food.source.split(' · ')[0]}`}
      </div>
    </div>
  );
}

function Row(props: { food: Food; onEdit: () => void }) {
  const del = useDeleteFood();
  const { food } = props;
  const onDelete = () => {
    if (window.confirm(`Supprimer « ${food.name} » et ses photos ?`)) {
      del.mutate(food.id);
    }
  };
  return (
    <li className="food-row">
      <Summary food={food} />
      <div className="row-actions">
        <button className="btn ghost" onClick={props.onEdit}>
          Modifier
        </button>
        <button className="btn ghost" onClick={onDelete}>
          Supprimer
        </button>
      </div>
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
  const [editing, setEditing] = useState<string | null>(null);
  return (
    <section className="card">
      <h2>Mes aliments ({foods.length})</h2>
      <p className="muted">{ABOUT}</p>
      <Editor editing={editing} foods={foods} onEdit={setEditing} />
      <ul className="food-list">
        {foods.map((food) => (
          <Row key={food.id} food={food} onEdit={() => setEditing(food.id)} />
        ))}
      </ul>
    </section>
  );
}
