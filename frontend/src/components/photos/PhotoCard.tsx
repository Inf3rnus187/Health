import type { Photo } from '../../api/photos';
import { usePhotoAnalysis } from '../../hooks/usePhotos';
import { AuthImage } from './AuthImage';

const ANGLE_LABEL: Record<string, string> = {
  face: 'Face',
  profil: 'Profil',
  dos: 'Dos',
};

const STATUS_LABEL: Record<string, string> = {
  received: 'Reçue',
  processing: 'Analyse…',
  analyzed: 'Analysée',
  failed: 'Échec',
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
    </div>
  );
}
