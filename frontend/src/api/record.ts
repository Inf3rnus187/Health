import { api } from './client';
import type { MetricOverview } from './overview';

export interface DocRef {
  id: string;
  title: string;
  date: string;
  kind: string;
}

export interface RecordDoc extends DocRef {
  status: string | null;
  summary: string | null;
  findings: string[];
  values: number;
}

export interface SuggestedCondition {
  name: string;
  documents: DocRef[];
}

export interface SuggestedTreatment {
  name: string;
  dose?: string;
  frequency?: string;
  documents: DocRef[];
}

export interface ResultPoint {
  date: string;
  value: number;
  source: string;
  document: DocRef | null;
}

export interface RecordResult {
  key: string;
  label: string;
  unit: string | null;
  latest: ResultPoint;
  previous: ResultPoint | null;
  change: number | null;
  count: number;
  history: { date: string; value: number }[];
}

export interface TimelineItem {
  date: string;
  type:
    | 'document'
    | 'condition'
    | 'treatment_start'
    | 'treatment_stop'
    | 'appointment';
  title: string;
  detail: string | null;
  id: string;
  kind: string | null;
}

export interface MedicalRecord {
  documents: RecordDoc[];
  suggested_conditions: SuggestedCondition[];
  suggested_treatments: SuggestedTreatment[];
  results: RecordResult[];
  timeline: TimelineItem[];
}

export interface CareCondition {
  id: string;
  name: string;
  status: string;
  indicators: MetricOverview[];
  documents: DocRef[];
}

/** The consolidated record (Dossier): documents, results, chronology. */
export function fetchRecord(): Promise<MedicalRecord> {
  return api<MedicalRecord>('/medical/record');
}

/** Each declared condition with its indicators and documents (Suivi). */
export function fetchCareOverview(): Promise<CareCondition[]> {
  return api<CareCondition[]>('/care/overview');
}
