import { MealForm } from '../components/journal/MealForm';
import { MealList } from '../components/journal/MealList';
import { UrinationCard } from '../components/journal/UrinationCard';

export function JournalPage() {
  return (
    <>
      <UrinationCard />
      <MealForm />
      <MealList />
    </>
  );
}
