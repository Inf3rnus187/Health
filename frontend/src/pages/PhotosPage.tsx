import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { deleteAllPhotos, type Photo } from '../api/photos';
import { PhotoCard } from '../components/photos/PhotoCard';
import { usePhotos } from '../hooks/usePhotos';

function DeleteAllButton() {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: deleteAllPhotos,
    onSuccess: () => void client.invalidateQueries({ queryKey: ['photos'] }),
  });
  const onClick = () => {
    if (window.confirm('Supprimer TOUTES les photos ?')) {
      mutation.mutate();
    }
  };
  return (
    <button className="btn btn-danger" type="button" onClick={onClick}>
      Tout supprimer
    </button>
  );
}

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

function Grid({ photos, loading }: { photos: Photo[]; loading: boolean }) {
  if (loading) {
    return <p className="muted">Chargement…</p>;
  }
  if (photos.length === 0) {
    return <p className="muted">Aucune photo pour l’instant.</p>;
  }
  return (
    <div className="photo-grid">
      {photos.map((photo) => (
        <PhotoCard key={photo.id} photo={photo} />
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
      <div className="photo-toolbar">
        <AngleFilter angle={angle} onAngle={setAngle} />
        {photos.length > 0 && <DeleteAllButton />}
      </div>
      <Grid photos={photos} loading={isLoading} />
    </section>
  );
}
