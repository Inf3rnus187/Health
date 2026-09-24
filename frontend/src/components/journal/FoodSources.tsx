import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import {
  type CiqualRef,
  type LabelReading,
  lookupBarcode,
  searchCiqual,
} from '../../api/foods';
import { frNumber } from '../../utils/format';

function RefButton(props: { r: CiqualRef; onPick: (r: CiqualRef) => void }) {
  const kcal = props.r.per_100g.energy_kcal;
  return (
    <li>
      <button
        type="button"
        className="linklike"
        onClick={() => props.onPick(props.r)}
      >
        {props.r.name}
      </button>{' '}
      <span className="muted small">
        {kcal == null ? '' : `${frNumber(kcal, 0)} kcal / 100 g`}
      </span>
    </li>
  );
}

function useCiqual(asked: string) {
  return useQuery({
    queryKey: ['ciqual', asked],
    queryFn: () => searchCiqual(asked),
    enabled: asked.length >= 2,
    staleTime: Infinity,
  });
}

/** Search the ANSES Ciqual table (offline) and take a food's values. */
export function CiqualSearch({ onPick }: { onPick: (r: CiqualRef) => void }) {
  const [q, setQ] = useState('');
  const asked = q.trim();
  const found = useCiqual(asked);
  const items = found.data?.items ?? [];
  return (
    <div className="food-source">
      <input
        className="input"
        value={q}
        placeholder="Chercher : tomate crue, saumon vapeur, riz cuit…"
        onChange={(e) => setQ(e.target.value)}
      />
      {asked.length >= 2 && items.length === 0 && !found.isFetching && (
        <p className="muted small">Rien dans la table Ciqual.</p>
      )}
      <ul className="food-refs">
        {items.map((r) => (
          <RefButton key={r.code} r={r} onPick={onPick} />
        ))}
      </ul>
    </div>
  );
}

/** A barcode looked up on Open Food Facts (when the hub allows it). */
export function BarcodeLookup(props: {
  onFound: (found: LabelReading) => void;
}) {
  const [code, setCode] = useState('');
  const look = useMutation({ mutationFn: lookupBarcode });
  const go = () =>
    look.mutate(code.replace(/\D/g, ''), { onSuccess: props.onFound });
  return (
    <div className="food-source">
      <div className="quick">
        <input
          className="input"
          inputMode="numeric"
          value={code}
          placeholder="13 chiffres sous le code-barres"
          onChange={(e) => setCode(e.target.value)}
        />
        <button type="button" className="btn ghost" onClick={go}>
          {look.isPending ? 'Recherche…' : 'Chercher'}
        </button>
      </div>
      {look.isError && <p className="error">{look.error.message}</p>}
    </div>
  );
}
