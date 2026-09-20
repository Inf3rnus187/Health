import { ClinicalCard } from '../components/ClinicalCard';
import { EcgCard } from '../components/EcgCard';
import { RoutesCard } from '../components/RoutesCard';
import { WorkoutsCard } from '../components/WorkoutsCard';

export function HealthPage() {
  return (
    <>
      <WorkoutsCard />
      <EcgCard />
      <RoutesCard />
      <ClinicalCard />
    </>
  );
}
