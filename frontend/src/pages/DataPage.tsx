import { DailyValuesCard } from '../components/data/DailyValuesCard';
import { InventoryCard } from '../components/data/InventoryCard';
import { SamplesBrowser } from '../components/SamplesBrowser';

export function DataPage() {
  return (
    <>
      <InventoryCard />
      <DailyValuesCard />
      <SamplesBrowser />
    </>
  );
}
