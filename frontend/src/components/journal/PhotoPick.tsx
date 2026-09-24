import { ShotButton, ShotPreview } from './Shots';

/** Photos of a meal at most: the plate, then boxes, sachets, labels. */
const MOST_PHOTOS = 7;

function Chosen(props: { photos: File[]; onDrop: (index: number) => void }) {
  return (
    <ul className="photo-pick-chosen">
      {props.photos.map((photo, index) => (
        <li key={`${photo.name}-${photo.lastModified}-${index}`}>
          <ShotPreview file={photo} />
          <button
            type="button"
            className="chip-x"
            title="Retirer"
            onClick={() => props.onDrop(index)}
          >
            ×
          </button>
          <span className="muted small">
            {index === 0 ? 'assiette' : 'emballage'}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Take photos or pick several from the gallery; show them, drop one. */
export function PhotoPick(props: {
  photos: File[];
  onChange: (photos: File[]) => void;
}) {
  const add = (files: File[]) =>
    props.onChange([...props.photos, ...files].slice(0, MOST_PHOTOS));
  const drop = (index: number) =>
    props.onChange(props.photos.filter((_, i) => i !== index));
  return (
    <div className="photo-pick">
      <span className="muted">
        Photos (facultatives) : l’assiette d’abord, puis la boîte, le sachet, le
        tableau des valeurs — {MOST_PHOTOS} au plus
      </span>
      <div className="quick">
        <ShotButton label="📷 Prendre une photo" camera onPick={add} />
        <ShotButton label="🖼️ Galerie" many onPick={add} />
      </div>
      {props.photos.length > 0 && (
        <Chosen photos={props.photos} onDrop={drop} />
      )}
    </div>
  );
}
