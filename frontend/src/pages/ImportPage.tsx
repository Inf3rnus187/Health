import { AutoExportCard } from '../components/AutoExportCard';
import { HealthKitAppCard } from '../components/HealthKitAppCard';
import { ImportPanel } from '../components/ImportPanel';
import { MobileSyncCard } from '../components/MobileSyncCard';
import { TokenManager } from '../components/TokenManager';

export function ImportPage() {
  return (
    <>
      <ImportPanel />
      <HealthKitAppCard />
      <AutoExportCard />
      <MobileSyncCard />
      <TokenManager />
    </>
  );
}
