import { useMutation, useQueryClient } from '@tanstack/react-query';

import { reanalyzePhoto, type Photo } from '../../api/photos';
import { usePhotoAnalysis } from '../../hooks/usePhotos';
import { AuthImage } from './AuthImage';

function ReanalyzeButton({ id }: { id: string }) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => reanalyzePhoto(id),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['photos'] });
      void client.invalidateQueries({ queryKey: ['photo-analysis', id] });
    },
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

const ANGLE_LABEL: Record<string, string> = {
  face: 'Face',
  profil: 'Profil',
  dos: 'Dos',
};

const STATUS_LABEL: Record<string, string> = {
  received: 'Reçue',
  normalized: 'Prête',
  analyzed: 'Analysée',
  ai_failed: 'IA indisponible',
  error: 'Image illisible',
};

function present(value: unknown): string {
  if (value === null || value === undefined) {
    return '—';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

function Analysis({ id }: { id: string }) {
  const { data, isError, isLoading } = usePhotoAnalysis(id);
  if (isLoading) {
    return <p className="muted">Analyse…</p>;
  }
  if (isError || !data) {
    return <p className="muted">Analyse IA en attente.</p>;
  }
  const rows = Object.entries(data.raw_output ?? {});
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

export function PhotoCard({ photo }: { photo: Photo }) {
  return (
    <div className="photo-card">
      <AuthImage id={photo.id} alt={photo.angle} />
      <div className="photo-meta">
        <strong>{ANGLE_LABEL[photo.angle] ?? photo.angle}</strong>
        <span className="muted">{photo.date_key}</span>
        {photo.linked_weight != null && (
          <span className="muted">{photo.linked_weight} kg</span>
        )}
        <span className="badge">
          {STATUS_LABEL[photo.status] ?? photo.status}
        </span>
      </div>
      <Analysis id={photo.id} />
      <div className="photo-actions">
        <ReanalyzeButton id={photo.id} />
      </div>
    </div>
  );
}
