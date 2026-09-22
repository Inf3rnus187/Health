import type { AnalysisV2, PhotoQuality } from '../../api/photos';
import { frNumber } from '../../utils/format';
import { Comparisons } from './Comparisons';

function QualityLine({ quality }: { quality?: PhotoQuality }) {
  if (!quality) {
    return null;
  }
  const issues = quality.issues ?? [];
  return (
    <p
      className={
        quality.ok ? 'analysis-line tone-ok' : 'analysis-line tone-bad'
      }
    >
      {quality.ok ? 'Qualité : OK' : 'Qualité insuffisante'}
      {issues.length > 0 && ` — ${issues.join(' · ')}`}
    </p>
  );
}

interface ScoresProps {
  scores: Record<string, number>;
  labels: Record<string, string>;
  rejected: boolean;
}

function Scores({ scores, labels, rejected }: ScoresProps) {
  const entries = Object.entries(scores).filter(
    ([, value]) => typeof value === 'number',
  );
  if (entries.length === 0) {
    const why = rejected ? ' (photo écartée par le contrôle qualité)' : '';
    return <p className="analysis-line muted">Pas de score{why}.</p>;
  }
  return (
    <ul className="score-list">
      {entries.map(([key, value]) => (
        <li key={key}>
          <span>{labels[key] ?? key} :</span>
          <strong>{frNumber(value)}/10</strong>
        </li>
      ))}
    </ul>
  );
}

function percent(confidence: number): string {
  const pct = confidence <= 1 ? confidence * 100 : confidence;
  return `${Math.round(pct)} %`;
}

interface ReliabilityProps {
  confidence?: number | null;
  poseOk?: boolean | null;
}

function Reliability({ confidence, poseOk }: ReliabilityProps) {
  const hasConfidence = typeof confidence === 'number';
  if (!hasConfidence && poseOk !== false) {
    return null;
  }
  return (
    <p className="analysis-line">
      {hasConfidence && (
        <span className="muted">Confiance : {percent(confidence)}</span>
      )}
      {poseOk === false && (
        <span className="tone-warn">Posture non conforme au protocole</span>
      )}
    </p>
  );
}

export function AnalysisV2View({ data }: { data: AnalysisV2 }) {
  const labels = data.labels ?? {};
  return (
    <div className="photo-analysis analysis-v2">
      <QualityLine quality={data.quality} />
      <Scores
        scores={data.scores ?? {}}
        labels={labels}
        rejected={data.quality?.ok === false}
      />
      <Reliability confidence={data.confidence} poseOk={data.pose_ok} />
      {data.remarks && <p className="analysis-remarks">{data.remarks}</p>}
      <Comparisons items={data.comparisons ?? []} labels={labels} />
    </div>
  );
}
