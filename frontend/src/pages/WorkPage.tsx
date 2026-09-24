import { ClockCard } from '../components/work/ClockCard';
import { MealSpending } from '../components/work/MealSpending';
import { DaysTable } from '../components/work/DaysTable';
import { SessionList } from '../components/work/SessionList';
import { WorkImport } from '../components/work/WorkImport';
import { WorkStatsCard } from '../components/work/WorkStatsCard';
import { AbsenceImport } from '../components/workfile/AbsenceImport';
import { AbsencesCard } from '../components/workfile/AbsencesCard';
import { EvidenceCard } from '../components/workfile/EvidenceCard';
import { FileSummary } from '../components/workfile/FileSummary';
import { Incomplete } from '../components/workfile/Incomplete';
import { LogsImport } from '../components/workfile/LogsImport';
import { NightsCard } from '../components/workfile/NightsCard';
import { TraceImport } from '../components/workfile/TraceImport';
import { useIncomplete } from '../hooks/useWorkFile';
import { useStored } from '../utils/stored';

const TABS = {
  jours: 'Journées',
  completer: 'À compléter',
  sessions: 'Sessions',
  stats: 'Statistiques',
  dossier: 'Dossier travail et santé',
  import: 'Importer',
};
type Tab = keyof typeof TABS;

function Dossier() {
  return (
    <>
      <FileSummary />
      <AbsencesCard />
      <EvidenceCard />
      <NightsCard />
    </>
  );
}

function Imports() {
  return (
    <>
      <LogsImport />
      <TraceImport />
      <AbsenceImport />
      <WorkImport />
    </>
  );
}

function content(tab: Tab, go: (tab: Tab) => void): JSX.Element {
  const pages: Record<Tab, () => JSX.Element> = {
    jours: () => (
      <>
        <ClockCard />
        <DaysTable toComplete={() => go('completer')} />
      </>
    ),
    completer: () => <Incomplete />,
    sessions: () => <SessionList />,
    stats: () => (
      <>
        <WorkStatsCard />
        <MealSpending />
      </>
    ),
    dossier: () => <Dossier />,
    import: () => <Imports />,
  };
  return pages[tab]();
}

function Tabs(props: { tab: Tab; go: (tab: Tab) => void }) {
  const todo = useIncomplete().data?.length ?? 0;
  return (
    <div className="tabs">
      {(Object.keys(TABS) as Tab[]).map((key) => (
        <button
          key={key}
          className={key === props.tab ? 'tab active' : 'tab'}
          onClick={() => props.go(key)}
        >
          {TABS[key]}
          {key === 'completer' && todo > 0 && ` (${todo})`}
        </button>
      ))}
    </div>
  );
}

/** Work: the days at a glance first, then what to complete, the rest. */
export function WorkPage() {
  const [tab, setTab] = useStored<Tab>('work.tab', 'jours', Object.keys(TABS));
  return (
    <>
      <Tabs tab={tab} go={setTab} />
      {content(tab, setTab)}
    </>
  );
}
