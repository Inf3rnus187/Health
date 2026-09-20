import { useState } from 'react';
import type { WheelEvent } from 'react';

import type { Bucket, TrendPoint } from '../api/types';
import { formatTick } from '../utils/formatTick';
import { zoomDomain } from '../utils/zoom';
import { TrendLines } from './TrendLines';

interface ZoomChartProps {
  points: TrendPoint[];
  color: string;
  label: string;
  bucket: Bucket;
}

type TimeDomain = [number, number] | ['dataMin', 'dataMax'];

export function ZoomChart({ points, color, label, bucket }: ZoomChartProps) {
  const [zoom, setZoom] = useState<[number, number] | null>(null);
  const min = points[0]?.t ?? 0;
  const max = points[points.length - 1]?.t ?? min;
  const onWheel = (event: WheelEvent) => {
    event.preventDefault();
    setZoom(zoomDomain(zoom, min, max, event.deltaY));
  };
  const domain: TimeDomain = zoom ?? ['dataMin', 'dataMax'];
  return (
    <div className="chart-zoom" onWheel={onWheel}>
      <TrendLines
        points={points}
        color={color}
        label={label}
        domain={domain}
        fmt={(ms) => formatTick(ms, bucket)}
      />
      <p className="chart-hint muted">Molette = zoom temporel</p>
    </div>
  );
}
