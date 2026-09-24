import { useState } from 'react';

import type { Meal } from '../api/journal';
import { FoodsCard } from '../components/journal/FoodsCard';
import { JournalDays } from '../components/journal/JournalDays';
import { type MealDraft, MealForm } from '../components/journal/MealForm';
import { MealList } from '../components/journal/MealList';
import { TodayCard } from '../components/journal/TodayCard';
import { useStored } from '../utils/stored';

const TABS = {
  jour: 'Aujourd’hui',
  repas: 'Repas',
  aliments: 'Mes aliments',
};
type Tab = keyof typeof TABS;

function Tabs(props: { tab: Tab; onSelect: (tab: Tab) => void }) {
  return (
    <div className="tabs">
      {(Object.keys(TABS) as Tab[]).map((key) => (
        <button
          key={key}
          className={key === props.tab ? 'tab active' : 'tab'}
          onClick={() => props.onSelect(key)}
        >
          {TABS[key]}
        </button>
      ))}
    </div>
  );
}

/** Meals: the form (a past meal can fill it again) and the list. */
function Meals() {
  const [draft, setDraft] = useState<{ n: number; d: MealDraft } | null>(null);
  const reuse = (meal: Meal) => {
    const d = { ...meal, foods: meal.foods ?? [] };
    setDraft((now) => ({ n: (now?.n ?? 0) + 1, d }));
    document.getElementById('meal-form')?.scrollIntoView();
  };
  return (
    <>
      <MealForm key={draft?.n ?? 0} draft={draft?.d ?? null} />
      <MealList onReuse={reuse} />
    </>
  );
}

export function JournalPage() {
  const [tab, setTab] = useStored<Tab>(
    'journal.tab',
    'jour',
    Object.keys(TABS),
  );
  return (
    <>
      <Tabs tab={tab} onSelect={setTab} />
      {tab === 'jour' && (
        <>
          <TodayCard />
          <JournalDays />
        </>
      )}
      {tab === 'repas' && <Meals />}
      {tab === 'aliments' && <FoodsCard />}
    </>
  );
}
