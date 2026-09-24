import { useState } from 'react';

/** A square thumbnail; a tap shows the whole picture, a tap closes it.
 *
 * ``small``: a 64 px thumbnail (a pack, a label, beside a meal). */
export function Zoomable(props: { src: string; alt: string; small?: boolean }) {
  const [open, setOpen] = useState(false);
  const size = props.small ? 'meal-photo mini-photo' : 'meal-photo';
  return (
    <>
      <button
        type="button"
        className="meal-thumb"
        title="Agrandir"
        onClick={() => setOpen(true)}
      >
        <img className={size} src={props.src} alt={props.alt} />
      </button>
      {open && (
        <div className="lightbox" onClick={() => setOpen(false)}>
          <img src={props.src} alt={props.alt} />
        </div>
      )}
    </>
  );
}
