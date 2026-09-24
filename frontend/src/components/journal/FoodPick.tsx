import { useState } from 'react';

import type { Food, FoodPortion } from '../../api/foods';
import { useFoods } from '../../hooks/useFoods';
import { frNumber } from '../../utils/format';

function Chip(props: { name: string; p: FoodPortion; onDrop: () => void }) {
  const { p } = props;
  return (
    <li className="chip">
      {props.name} ·{' '}
      {p.grams == null ? 'quantité estimée' : `${frNumber(p.grams, 0)} g`}
      <button
        type="button"
        className="chip-x"
        title="Retirer"
        onClick={props.onDrop}
      >
        ×
      </button>
    </li>
  );
}

function Chosen(props: {
  value: FoodPortion[];
  foods: Food[];
  onDrop: (id: string) => void;
}) {
  const name = (id: string) =>
    props.foods.find((f) => f.id === id)?.name ?? 'aliment supprimé';
  return (
    <ul className="chips">
      {props.value.map((p) => (
        <Chip
          key={p.food_id}
          name={name(p.food_id)}
          p={p}
          onDrop={() => props.onDrop(p.food_id)}
        />
      ))}
    </ul>
  );
}

function usePick(value: FoodPortion[], onChange: (v: FoodPortion[]) => void) {
  const [id, setId] = useState('');
  const [grams, setGrams] = useState('');
  const add = () => {
    if (!id) return;
    const g = Number.parseFloat(grams.replace(',', '.'));
    const rest = value.filter((p) => p.food_id !== id);
    onChange([...rest, { food_id: id, grams: g > 0 ? g : null }]);
    setId('');
    setGrams('');
  };
  const drop = (gone: string) =>
    onChange(value.filter((p) => p.food_id !== gone));
  return { id, setId, grams, setGrams, add, drop };
}

function Select(props: { foods: Food[]; p: ReturnType<typeof usePick> }) {
  return (
    <select
      className="input"
      value={props.p.id}
      onChange={(e) => props.p.setId(e.target.value)}
    >
      <option value="">Choisir…</option>
      {props.foods.map((f) => (
        <option key={f.id} value={f.id}>
          {f.name}
        </option>
      ))}
    </select>
  );
}

function Choose(props: { foods: Food[]; p: ReturnType<typeof usePick> }) {
  const { p } = props;
  return (
    <div className="quick">
      <Select foods={props.foods} p={p} />
      <input
        className="input"
        inputMode="decimal"
        placeholder="grammes"
        title="Vide : la quantité est estimée"
        value={p.grams}
        onChange={(e) => p.setGrams(e.target.value)}
      />
      <button type="button" className="btn ghost" onClick={p.add}>
        Ajouter
      </button>
    </div>
  );
}

/** The foods of « Mes aliments » eaten in this meal, and how much. */
export function FoodPick(props: {
  value: FoodPortion[];
  onChange: (value: FoodPortion[]) => void;
}) {
  const foods = useFoods().data ?? [];
  const p = usePick(props.value, props.onChange);
  if (foods.length === 0) return null;
  return (
    <div className="photo-pick">
      <span className="muted">
        Aliments de ma liste, calculés avec leur fiche (grammes vides : lus dans
        la description, sinon estimés ; un aliment nommé dans la description est
        reconnu aussi)
      </span>
      <Choose foods={foods} p={p} />
      <Chosen value={props.value} foods={foods} onDrop={p.drop} />
    </div>
  );
}
