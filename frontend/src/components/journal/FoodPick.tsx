import { useState } from 'react';

import type { Food, FoodPortion, ScanResult } from '../../api/foods';
import { useFoods } from '../../hooks/useFoods';
import { frNumber } from '../../utils/format';
import { BarcodeScan } from './BarcodeScan';

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

/** What a scan did to the choice, in words. */
function scanned(r: ScanResult): string {
  const code = r.barcodes[0];
  if (!code) return r.note || 'Aucun code-barres lisible';
  if (r.food) return `« ${r.food.name} » choisi : grammes puis Ajouter.`;
  return `Produit ${code} absent de vos aliments : créez sa fiche.`;
}

/** Scan a pack: my food with that barcode gets chosen in the list. */
function Scan(props: { p: ReturnType<typeof usePick> }) {
  const [open, setOpen] = useState(false);
  const [said, setSaid] = useState('');
  const onResult = (r: ScanResult) => {
    setSaid(scanned(r));
    if (r.food) props.p.setId(r.food.id);
  };
  return (
    <>
      <div className="quick">
        <button
          type="button"
          className="btn ghost"
          onClick={() => setOpen(!open)}
        >
          ▥ Scanner un code-barres
        </button>
      </div>
      {open && <BarcodeScan onResult={onResult} />}
      {open && said && <p className="muted small">{said}</p>}
    </>
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
      <Scan p={p} />
      <Chosen value={props.value} foods={foods} onDrop={p.drop} />
    </div>
  );
}
