import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import {
  type CiqualRef,
  type LabelReading,
  lookupBarcode,
  type ScanResult,
  searchCiqual,
} from '../../api/foods';
import { frNumber } from '../../utils/format';
import { BarcodeScan } from './BarcodeScan';
import { foodName } from './foodLabel';

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

/** What a scan found, in words. */
function scanText(r: ScanResult): string {
  const code = r.barcodes[0];
  if (!code) return r.note || 'Aucun code-barres lisible';
  if (r.food)
    return `Code ${code} : déjà dans vos aliments (« ${foodName(r.food)} »).`;
  if (r.product)
    return `Code ${code} : trouvé sur Open Food Facts, à vérifier.`;
  const why = r.online ? r.note : 'recherche en ligne désactivée';
  return `Code ${code} lu (${why}) : remplissez les valeurs vous-même.`;
}

function useLookup(props: BarcodeProps) {
  const [code, setCode] = useState(props.initial ?? '');
  const [said, setSaid] = useState('');
  const look = useMutation({ mutationFn: lookupBarcode });
  const go = () =>
    look.mutate(code.replace(/\D/g, ''), { onSuccess: props.onFound });
  const onScan = (r: ScanResult) => {
    setSaid(scanText(r));
    const found = r.barcodes[0];
    if (!found) return;
    setCode(found);
    if (r.product) props.onFound(r.product);
    else props.onCode(found);
  };
  return { code, setCode, said, look, go, onScan };
}

interface BarcodeProps {
  onFound: (found: LabelReading) => void;
  onCode: (code: string) => void;
  /** The sheet's barcode: « Chercher » reads its product page again. */
  initial?: string;
}

/** A barcode scanned (camera, photo) or typed; Open Food Facts if allowed. */
export function BarcodeLookup(props: BarcodeProps) {
  const b = useLookup(props);
  return (
    <div className="food-source">
      <BarcodeScan onResult={b.onScan} />
      {b.said && <p className="muted small">{b.said}</p>}
      <div className="quick">
        <input
          className="input"
          inputMode="numeric"
          value={b.code}
          placeholder="ou les 13 chiffres sous le code-barres"
          onChange={(e) => b.setCode(e.target.value)}
        />
        <button type="button" className="btn ghost" onClick={b.go}>
          {b.look.isPending ? 'Recherche…' : 'Chercher'}
        </button>
      </div>
      {b.look.isError && <p className="error">{b.look.error.message}</p>}
    </div>
  );
}
