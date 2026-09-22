import {
  useMutation,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query';

import {
  asAnalysisV2,
  deletePhoto,
  reanalyzePhoto,
  type Photo,
} from '../../api/photos';
import { usePhotoAnalysis } from '../../hooks/usePhotos';
import { AnalysisV2View } from './AnalysisV2';
import { AuthImage } from './AuthImage';
import { angleLabel, STATUS_LABEL } from './labels';

const REFRESH_DELAYS = [1500, 4000, 8000, 13000];

function refreshLater(client: QueryClient, id: string): void {
  for (const delay of REFRESH_DELAYS) {
    setTimeout(() => {
      void client.invalidateQueries({ queryKey: ['photos'] });
      void client.invalidateQueries({ queryKey: ['photo-analysis', id] });
      void client.invalidateQueries({ queryKey: ['evolution-trend'] });
    }, delay);
  }
}

function ReanalyzeButton({ id }: { id: string }) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => reanalyzePhoto(id),
    onSuccess: () => refreshLater(client, id),
  });
  return (
    <button
      className="btn btn-ghost"
      type="button"
      disabled={mutation.isPending}
      onClick={() => mutation.mutate()}
    >
      {mutation.isPending ? 'Relance…' : 'Relancer l’analyse'}
    </button>
  );
}

function DeleteButton({ id }: { id: string }) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => deletePhoto(id),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['photos'] });
      void client.invalidateQueries({ queryKey: ['evolution-trend'] });
    },
  });
  const onClick = () => {
    if (window.confirm('Supprimer cette photo ?')) {
      mutation.mutate();
    }
  };
  return (
    <button
      className="btn btn-danger"
      type="button"
      disabled={mutation.isPending}
      onClick={onClick}
    >
      Supprimer
    </button>
  );
}

function present(value: unknown): string {
  if (value === null || value === undefined) {
    return '—';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

// v1 analyses (no `method` key): generic key/value dump.
function GenericAnalysis({ raw }: { raw: Record<string, unknown> | null }) {
  const rows = Object.entries(raw ?? {});
  return (
    <dl className="photo-analysis">
      {rows.map(([key, value]) => (
        <div key={key}>
          <dt>{key}</dt>
          <dd>{present(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function Analysis({ id }: { id: string }) {
  const { data, isError, isLoading } = usePhotoAnalysis(id);
  if (isLoading) {
    return <p className="muted photo-pending">Analyse…</p>;
  }
  if (isError || !data) {
    return <p className="muted photo-pending">Analyse IA en attente.</p>;
  }
  const v2 = asAnalysisV2(data.raw_output);
  if (v2) {
    return <AnalysisV2View data={v2} />;
  }
  return <GenericAnalysis raw={data.raw_output} />;
}

export function PhotoCard({ photo }: { photo: Photo }) {
  return (
    <div className="photo-card">
      <AuthImage id={photo.id} alt={photo.angle} />
      <div className="photo-meta">
        <strong>{angleLabel(photo.angle)}</strong>
        <span className="muted">{photo.date_key}</span>
        {photo.linked_weight != null && (
          <span className="muted">{photo.linked_weight} kg</span>
        )}
        <span className={`badge status-${photo.status}`}>
          {STATUS_LABEL[photo.status] ?? photo.status}
        </span>
      </div>
      <Analysis id={photo.id} />
      <div className="photo-actions">
        <ReanalyzeButton id={photo.id} />
        <DeleteButton id={photo.id} />
      </div>
    </div>
  );
}
