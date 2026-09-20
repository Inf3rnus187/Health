import { useState } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';

import type { Bucket, Trend, TrendPoint } from '../api/types';
import { useTrend } from '../hooks/useTrend';
import { colorForMetric } from '../theme/palette';
import { toPoints } from '../utils/points';
import { PeriodTabs } from './PeriodTabs';
import { ZoomChart } from './ZoomChart';

interface TrendChartProps {
  metricKey: string;
  label: string;
}

interface StateProps {
  query: UseQueryResult<Trend>;
  bucket: Bucket;
  token: number;
  color: string;
  label: string;
}

function Body(props: {
  token: number;
  bucket: Bucket;
  points: TrendPoint[];
  color: string;
  label: string;
}) {
  if (props.points.length === 0) {
    return <p className="muted">Aucune donnée.</p>;
  }
  return (
    <ZoomChart
      key={`${props.bucket}-${props.token}`}
      points={props.points}
      color={props.color}
      label={props.label}
      bucket={props.bucket}
    />
  );
}

function TrendState({ query, bucket, token, color, label }: StateProps) {
  if (query.isError) {
    return <p className="error">Erreur : {(query.error as Error).message}</p>;
  }
  if (query.isPending) {
    return <p className="muted">Chargement…</p>;
  }
  return (
    <Body
      token={token}
      bucket={bucket}
      points={toPoints(query.data)}
      color={color}
      label={label}
    />
  );
}

export function TrendChart({ metricKey, label }: TrendChartProps) {
  const [bucket, setBucket] = useState<Bucket>('month');
  const [token, setToken] = useState(0);
  const query = useTrend(metricKey, bucket);
  return (
    <div>
      <PeriodTabs
        bucket={bucket}
        onBucket={setBucket}
        onReset={() => setToken((count) => count + 1)}
      />
      <TrendState
        query={query}
        bucket={bucket}
        token={token}
        color={colorForMetric(metricKey)}
        label={label}
      />
    </div>
  );
}
