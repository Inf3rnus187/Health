import { useRouteTrack } from '../hooks/useSignals';
import { RouteMap } from './RouteMap';

interface RouteViewerProps {
  id: string;
  onClose: () => void;
}

export function RouteViewer({ id, onClose }: RouteViewerProps) {
  const { data, isPending } = useRouteTrack(id);
  return (
    <div className="viewer">
      <div className="viewer-head">
        <span className="muted">
          Tracé GPS · {data?.points.length ?? 0} points
        </span>
        <button className="btn ghost" onClick={onClose}>
          Fermer
        </button>
      </div>
      {isPending ? (
        <p className="muted">Chargement…</p>
      ) : (
        <RouteMap points={data?.points ?? []} />
      )}
    </div>
  );
}
