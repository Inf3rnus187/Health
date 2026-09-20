import { useEcgSeries } from '../hooks/useSignals';
import { WaveformSvg } from './WaveformSvg';

interface EcgViewerProps {
  id: string;
  onClose: () => void;
}

export function EcgViewer({ id, onClose }: EcgViewerProps) {
  const { data, isPending } = useEcgSeries(id);
  return (
    <div className="viewer">
      <div className="viewer-head">
        <span className="muted">
          Tracé ECG · {data?.sample_rate_hz ?? '—'} Hz
        </span>
        <button className="btn ghost" onClick={onClose}>
          Fermer
        </button>
      </div>
      {isPending ? (
        <p className="muted">Chargement…</p>
      ) : (
        <WaveformSvg values={data?.values ?? []} />
      )}
    </div>
  );
}
