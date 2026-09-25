import { type FoodDraft, num } from './foodDraft';

const SHARES: [number, string][] = [
  [1, 'Toute la boîte'],
  [0.5, '½'],
  [0.25, '¼'],
];

type Set = (change: Partial<FoodDraft>) => void;

/** « Toute la boîte », « ½ », « ¼ »: a share of the package, in grams. */
function Shares(props: { pack: number; set: Set }) {
  const grams = (share: number) => String(+(props.pack * share).toFixed(1));
  return (
    <div className="quick">
      {SHARES.map(([share, label]) => (
        <button
          key={label}
          type="button"
          className="btn ghost"
          onClick={() => props.set({ portion_g: grams(share) })}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/** What I usually eat of it: a meal naming it without a quantity. */
export function PortionField({ draft, set }: { draft: FoodDraft; set: Set }) {
  const pack = num(draft.package_g);
  return (
    <div className="field">
      <label className="field">
        Ma portion habituelle (g) — comptée quand le repas ne dit pas combien
        <input
          className="input"
          inputMode="decimal"
          placeholder={pack ? `ex. ${pack} (toute la boîte)` : 'ex. 150'}
          value={draft.portion_g}
          onChange={(event) => set({ portion_g: event.target.value })}
        />
      </label>
      {pack != null && pack > 0 && <Shares pack={pack} set={set} />}
    </div>
  );
}
