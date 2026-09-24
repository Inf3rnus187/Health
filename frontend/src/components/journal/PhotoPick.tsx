import { type ChangeEvent, useEffect, useState } from 'react';

/** A preview of the photo picked (its object URL freed when replaced). */
function Preview({ photo }: { photo: File }) {
  const [url, setUrl] = useState('');
  useEffect(() => {
    const made = URL.createObjectURL(photo);
    setUrl(made);
    return () => URL.revokeObjectURL(made);
  }, [photo]);
  return url ? <img className="photo-pick-preview" src={url} alt="" /> : null;
}

function Source(props: {
  label: string;
  camera: boolean;
  onPick: (photo: File | null) => void;
}) {
  const pick = (event: ChangeEvent<HTMLInputElement>) => {
    props.onPick(event.target.files?.[0] ?? null);
    event.target.value = ''; // the same photo can be picked again
  };
  return (
    <label className="btn ghost">
      {props.label}
      <input
        type="file"
        accept="image/*"
        hidden
        capture={props.camera ? 'environment' : undefined}
        onChange={pick}
      />
    </label>
  );
}

function Chosen(props: { photo: File; onDrop: () => void }) {
  return (
    <div className="photo-pick-chosen">
      <Preview photo={props.photo} />
      <button type="button" className="btn ghost" onClick={props.onDrop}>
        Retirer la photo
      </button>
    </div>
  );
}

/** Take a photo or pick one from the gallery; show it, or take it back. */
export function PhotoPick(props: {
  photo: File | null;
  onPick: (photo: File | null) => void;
}) {
  return (
    <div className="photo-pick">
      <span className="muted">Photo du repas (facultative)</span>
      <div className="quick">
        <Source label="📷 Prendre une photo" camera onPick={props.onPick} />
        <Source label="🖼️ Galerie" camera={false} onPick={props.onPick} />
      </div>
      {props.photo && (
        <Chosen photo={props.photo} onDrop={() => props.onPick(null)} />
      )}
    </div>
  );
}
