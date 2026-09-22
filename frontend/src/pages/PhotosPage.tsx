import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { deleteAllPhotos, type Photo } from '../api/photos';
import { EvolutionView } from '../components/evolution/EvolutionView';
import { PhotoCard } from '../components/photos/PhotoCard';
import { usePhotos } from '../hooks/usePhotos';

function DeleteAllButton() {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: deleteAllPhotos,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['photos'] });
      void client.invalidateQueries({ queryKey: ['evolution-trend'] });
    },
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

interface TabItem<T extends string> {
  id: T;
  label: string;
}

type View = 'evolution' | 'gallery';

const VIEWS: TabItem<View>[] = [
  { id: 'evolution', label: 'Évolution' },
  { id: 'gallery', label: 'Galerie' },
];

const ANGLES: TabItem<string>[] = [
  { id: '', label: 'Toutes' },
  { id: 'face', label: 'Face' },
  { id: 'profil', label: 'Profil' },
  { id: 'dos', label: 'Dos' },
];

interface TabsProps<T extends string> {
  items: TabItem<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}

function Tabs<T extends string>(props: TabsProps<T>) {
  const { items, value, onChange, className } = props;
  return (
    <div className={className ? `tabs ${className}` : 'tabs'}>
      {items.map((item) => (
        <button
          key={item.id || 'all'}
          type="button"
          className={item.id === value ? 'tab active' : 'tab'}
          onClick={() => onChange(item.id)}
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

function Gallery() {
  const [angle, setAngle] = useState('');
  const { data, isLoading } = usePhotos(angle || undefined);
  const photos = data ?? [];
  return (
    <div className="gallery">
      <div className="photo-toolbar">
        <Tabs items={ANGLES} value={angle} onChange={setAngle} />
        {photos.length > 0 && <DeleteAllButton />}
      </div>
      <Grid photos={photos} loading={isLoading} />
    </div>
  );
}

export function PhotosPage() {
  const [view, setView] = useState<View>('evolution');
  return (
    <>
      <section className="card">
        <h2>Photos de suivi</h2>
        <Tabs
          items={VIEWS}
          value={view}
          onChange={setView}
          className="view-tabs"
        />
        {view === 'gallery' && <Gallery />}
      </section>
      {view === 'evolution' && <EvolutionView />}
    </>
  );
}
