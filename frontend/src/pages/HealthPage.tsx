import { ClinicalCard } from '../components/ClinicalCard';
import { EcgCard } from '../components/EcgCard';
import { RecordsHint } from '../components/RecordsHint';
import { RoutesCard } from '../components/RoutesCard';
import { VitalsSection } from '../components/VitalsSection';
import { WorkoutsCard } from '../components/WorkoutsCard';

export function HealthPage() {
  return (
    <>
      <VitalsSection />
      <WorkoutsCard />
      <EcgCard />
      <RoutesCard />
      <ClinicalCard />
      <RecordsHint />
    </>
  );
}
