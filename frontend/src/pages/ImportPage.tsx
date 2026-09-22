import { AutoExportCard } from '../components/AutoExportCard';
import { ImportPanel } from '../components/ImportPanel';
import { MobileSyncCard } from '../components/MobileSyncCard';
import { TokenManager } from '../components/TokenManager';

export function ImportPage() {
  return (
    <>
      <ImportPanel />
      <AutoExportCard />
      <MobileSyncCard />
      <TokenManager />
    </>
  );
}
