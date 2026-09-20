import { AppointmentsCard } from '../components/care/AppointmentsCard';
import { ConditionsCard } from '../components/care/ConditionsCard';
import { TreatmentsCard } from '../components/care/TreatmentsCard';

export function CarePage() {
  return (
    <>
      <ConditionsCard />
      <TreatmentsCard />
      <AppointmentsCard />
    </>
  );
}
