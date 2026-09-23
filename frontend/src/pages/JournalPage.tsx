import { JournalDays } from '../components/journal/JournalDays';
import { MealForm } from '../components/journal/MealForm';
import { MealList } from '../components/journal/MealList';
import { TodayCard } from '../components/journal/TodayCard';

export function JournalPage() {
  return (
    <>
      <TodayCard />
      <JournalDays />
      <MealForm />
      <MealList />
    </>
  );
}
