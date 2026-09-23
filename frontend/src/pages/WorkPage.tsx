import { ClockCard } from '../components/work/ClockCard';
import { SessionList } from '../components/work/SessionList';
import { WorkImport } from '../components/work/WorkImport';
import { WorkStatsCard } from '../components/work/WorkStatsCard';

/** Work hours: clock in / out, statistics, sessions, import. */
export function WorkPage() {
  return (
    <>
      <ClockCard />
      <WorkStatsCard />
      <SessionList />
      <WorkImport />
    </>
  );
}
