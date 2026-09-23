import type { Meal } from '../../api/journal';
import { useMeals } from '../../hooks/useJournal';
import { frNumber, shortDate } from '../../utils/format';
import { useRange } from '../../utils/range';
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

/** Meals of a period, grouped by day (a page is 10 days) with totals. */
export function MealList() {
  const [range, setRange] = useRange(7);
  const meals = useMeals(range).data ?? [];
  const { page, bar } = usePaging(byDay(meals));
  return (
    <section className="card">
      <h2>Repas ({meals.length})</h2>
      <DateRange value={range} onChange={setRange} />
      {meals.length === 0 && <p className="muted">Aucun repas noté.</p>}
      {bar}
      {page.map(([day, list]) => (
        <div key={day} className="meal-day">
          <h3>{shortDate(day)}</h3>
          <DayTotal meals={list} />
          {list.map((meal) => (
            <MealCard key={meal.id} meal={meal} />
          ))}
        </div>
      ))}
    </section>
  );
}
