import { MEAL_TYPES, type MealTotals } from '../../api/journal';
import type { MealReference, ReferenceRow } from '../../api/nutrition';
import { frNumber } from '../../utils/format';

const ROWS: [keyof MealTotals, string, string][] = [
  ['energy_kcal', 'Énergie', 'kcal'],
  ['protein_g', 'Protéines', 'g'],
  ['carbs_g', 'Glucides', 'g'],
  ['sugars_g', '— dont sucres', 'g'],
  ['fat_g', 'Lipides', 'g'],
  ['sat_fat_g', '— dont saturés', 'g'],
  ['fiber_g', 'Fibres', 'g'],
  ['sodium_mg', 'Sodium', 'mg'],
];

/** kind.verdict → symbol, style, meaning. */
const MARKS: Record<string, [string, string, string]> = {
  'limit.below': ['✓', 'ref-ok', 'sous la limite de ce repas'],
  'limit.within': ['✓', 'ref-ok', 'sous la limite de ce repas'],
  'limit.above': ['⚠', 'ref-warn', 'au-dessus de la limite de ce repas'],
  'target.below': ['↓', 'ref-warn', 'en dessous du repère : à augmenter'],
  'target.within': ['✓', 'ref-ok', 'repère atteint'],
  'target.above': ['✓', 'ref-ok', 'repère atteint'],
  'reference.below': ['↓', 'muted', 'en dessous du repère'],
  'reference.within': ['✓', 'ref-ok', 'dans le repère'],
  'reference.above': ['↑', 'muted', 'au-dessus du repère'],
};

/** « 600–800 kcal » (the meal's part) or « 33 % » of the day (a snack). */
function part(r: ReferenceRow): string {
  if (r.low == null || r.high == null) return `${r.day_pct} %`;
  return `${frNumber(r.low)}–${frNumber(r.high)} ${r.unit}`;
}

function RefCells({ r }: { r?: ReferenceRow }) {
  if (!r) return null;
  const whole =
    `${r.day_pct} % du repère d’un jour : ` +
    `${frNumber(r.day)} ${r.unit} (${r.source})`;
  const [mark, style, meaning] = MARKS[`${r.kind}.${r.verdict}`] ?? [];
  return (
    <>
      <td className="muted" title={whole}>
        {part(r)}
      </td>
      <td className={style} title={meaning} aria-label={meaning}>
        {mark}
      </td>
    </>
  );
}

function Head({ reference }: { reference: MealReference }) {
  const type = MEAL_TYPES[reference.meal_type] ?? reference.meal_type;
  const title = reference.share_pct
    ? `Repère ${type.toLowerCase()}`
    : 'Part du jour';
  return (
    <thead>
      <tr>
        <th />
        <th>Ce repas</th>
        <th>{title}</th>
        <th />
      </tr>
    </thead>
  );
}

/** What the reference column means, under the table. */
function Legend({ reference }: { reference: MealReference }) {
  const share = reference.share_pct;
  const text = share
    ? `Repère : ${share[0]}–${share[1]} % d’une journée d’adulte-type ` +
      '(indicatif). ✓ dans le repère · ↓ en dessous · ↑ au-dessus · ' +
      '⚠ limite dépassée.'
    : 'Part du repère d’une journée d’adulte-type ; aucune part n’est ' +
      'fixée pour une collation.';
  return <p className="muted small">{text}</p>;
}

/** The meal's nutrients, each against its official reference. */
export function NutrientTable(props: {
  totals: MealTotals;
  reference?: MealReference | null;
}) {
  const { totals, reference } = props;
  return (
    <>
      <table className="nutri-table">
        {reference && <Head reference={reference} />}
        <tbody>
          {ROWS.map(([key, label, unit]) => (
            <tr key={key}>
              <td>{label}</td>
              <td>
                {frNumber(totals[key], key === 'energy_kcal' ? 0 : 1)} {unit}
              </td>
              <RefCells r={reference?.rows[key]} />
            </tr>
          ))}
        </tbody>
      </table>
      {reference && <Legend reference={reference} />}
    </>
  );
}
