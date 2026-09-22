import { useState } from 'react';

import { PhotoCard } from '../components/photos/PhotoCard';
import { usePhotos } from '../hooks/usePhotos';

const ANGLES: { id: string; label: string }[] = [
  { id: '', label: 'Toutes' },
  { id: 'face', label: 'Face' },
  { id: 'profil', label: 'Profil' },
  { id: 'dos', label: 'Dos' },
];

function AngleFilter({
  angle,
  onAngle,
}: {
  angle: string;
  onAngle: (value: string) => void;
}) {
  return (
    <div className="tabs">
      {ANGLES.map((item) => (
        <button
          key={item.id || 'all'}
          className={item.id === angle ? 'tab active' : 'tab'}
          onClick={() => onAngle(item.id)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function PhotosPage() {
  const [angle, setAngle] = useState('');
  const { data, isLoading } = usePhotos(angle || undefined);
  const photos = data ?? [];
  return (
    <section className="card">
      <h2>Photos de suivi</h2>
      <p className="muted">
        Envoyées via l’API `POST /ingest/photo` (miroir, appareil) et analysées
        par l’IA. Cliquez un onglet pour filtrer par angle.
      </p>
      <AngleFilter angle={angle} onAngle={setAngle} />
      {isLoading && <p className="muted">Chargement…</p>}
      {!isLoading && photos.length === 0 && (
        <p className="muted">Aucune photo pour l’instant.</p>
      )}
      <div className="photo-grid">
        {photos.map((photo) => (
          <PhotoCard key={photo.id} photo={photo} />
        ))}
      </div>
    </section>
  );
}
