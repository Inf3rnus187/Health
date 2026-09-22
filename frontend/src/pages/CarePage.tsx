import { AppointmentsCard } from '../components/care/AppointmentsCard';
import { ConditionFollowCard } from '../components/care/ConditionFollowCard';
import { ConditionsCard } from '../components/care/ConditionsCard';
import { TreatmentsCard } from '../components/care/TreatmentsCard';
import { SuggestionsCard } from '../components/record/SuggestionsCard';

export function CarePage() {
  return (
    <>
      <ConditionFollowCard />
      <SuggestionsCard />
      <ConditionsCard />
      <TreatmentsCard />
      <AppointmentsCard />
    </>
  );
}
