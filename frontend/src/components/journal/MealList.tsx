import type { Meal } from '../../api/journal';
import { useMeals } from '../../hooks/useJournal';
import { type Selection, useSelection } from '../../hooks/useSelection';
import { frNumber, shortDate } from '../../utils/format';
import { useRange } from '../../utils/range';
import { BulkBar } from '../Bulk';
import { DateRange } from '../DateRange';
import { usePaging } from '../Paging';
import { MealCard } from './MealCard';

function byDay(meals: Meal[]): [string, Meal[]][] {
  const out = new Map<string, Meal[]>();
  for (const meal of meals) {
    out.set(meal.date_key, [...(out.get(meal.date_key) ?? []), meal]);
  }
  return [...out.entries()];
}

type Total = 'energy_kcal' | 'protein_g' | 'carbs_g' | 'fat_g';

function DayTotal({ meals }: { meals: Meal[] }) {
  const sum = (key: Total, digits = 0) =>
    frNumber(
      meals.reduce((acc, m) => acc + (m.analysis?.totals?.[key] ?? 0), 0),
      digits,
    );
  const text =
    `${sum('energy_kcal')} kcal · protéines ${sum('protein_g')} g · ` +
    `glucides ${sum('carbs_g')} g · lipides ${sum('fat_g')} g`;
  return <p className="muted">{text} (repas analysés)</p>;
}

type Reuse = (meal: Meal) => void;

function Day(props: {
  day: string;
  list: Meal[];
  sel: Selection;
  onReuse: Reuse;
}) {
  return (
    <div className="meal-day">
      <h3>{shortDate(props.day)}</h3>
      <DayTotal meals={props.list} />
      {props.list.map((meal) => (
        <MealCard
          key={meal.id}
          meal={meal}
          sel={props.sel}
          onReuse={props.onReuse}
        />
      ))}
    </div>
  );
}

const NOUN = 'repas (avec photos et nutriments)';

/** Meals of a period, grouped by day (a page is 10 days) with totals. */
export function MealList({ onReuse }: { onReuse: Reuse }) {
  const [range, setRange] = useRange(7, 'journal.meals');
  const meals = useMeals(range).data ?? [];
  const sel = useSelection();
  const { page, bar } = usePaging(byDay(meals));
  const ids = meals.map((m) => m.id);
  return (
    <section className="card">
      <h2>Repas ({meals.length})</h2>
      <DateRange value={range} onChange={setRange} />
      {meals.length === 0 && <p className="muted">Aucun repas noté.</p>}
      <BulkBar what="meals" noun={NOUN} shown={ids} sel={sel} />
      {bar}
      {page.map(([day, list]) => (
        <Day key={day} day={day} list={list} sel={sel} onReuse={onReuse} />
      ))}
    </section>
  );
}
