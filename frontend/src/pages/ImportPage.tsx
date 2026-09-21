import { AutoExportCard } from '../components/AutoExportCard';
import { ImportPanel } from '../components/ImportPanel';
import { MobileSyncCard } from '../components/MobileSyncCard';

export function ImportPage() {
  return (
    <>
      <ImportPanel />
      <AutoExportCard />
      <MobileSyncCard />
    </>
  );
}
