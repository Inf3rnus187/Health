import { useState } from 'react';

import { ClockCard } from '../components/work/ClockCard';
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

const TABS = {
  pointage: 'Pointage',
  dossier: 'Dossier travail et santé',
  import: 'Importer',
};
type Tab = keyof typeof TABS;

const CONTENT: Record<Tab, () => JSX.Element> = {
  pointage: () => (
    <>
      <ClockCard />
      <WorkStatsCard />
      <Incomplete />
      <SessionList />
    </>
  ),
  dossier: () => (
    <>
      <FileSummary />
      <AbsencesCard />
      <EvidenceCard />
      <NightsCard />
    </>
  ),
  import: () => (
    <>
      <LogsImport />
      <TraceImport />
      <AbsenceImport />
      <WorkImport />
    </>
  ),
};

/** Work hours and the work ↔ health file. */
export function WorkPage() {
  const [tab, setTab] = useState<Tab>('pointage');
  return (
    <>
      <div className="tabs">
        {(Object.keys(TABS) as Tab[]).map((key) => (
          <button
            key={key}
            className={key === tab ? 'tab active' : 'tab'}
            onClick={() => setTab(key)}
          >
            {TABS[key]}
          </button>
        ))}
      </div>
      {CONTENT[tab]()}
    </>
  );
}
