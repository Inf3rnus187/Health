import type { Meal } from '../../api/journal';
import { useMeals } from '../../hooks/useJournal';
import { frNumber, localToday, shortDate } from '../../utils/format';
import { MealCard } from './MealCard';

const DAYS = 7;

function daysAgo(n: number): string {
  const day = new Date(`${localToday()}T12:00:00`);
  day.setDate(day.getDate() - n);
  return day.toISOString().slice(0, 10);
}

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

/** The last 7 days of meals, grouped by day with the day's totals. */
export function MealList() {
  const meals = useMeals(daysAgo(DAYS - 1), localToday()).data ?? [];
  return (
    <section className="card">
      <h2>Repas des 7 derniers jours</h2>
      {meals.length === 0 && <p className="muted">Aucun repas noté.</p>}
      {byDay(meals).map(([day, list]) => (
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
