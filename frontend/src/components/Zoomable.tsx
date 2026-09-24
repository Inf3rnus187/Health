import { useState } from 'react';

/** A square thumbnail; a tap shows the whole picture, a tap closes it. */
export function Zoomable(props: { src: string; alt: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        className="meal-thumb"
        title="Agrandir"
        onClick={() => setOpen(true)}
      >
        <img className="meal-photo" src={props.src} alt={props.alt} />
      </button>
      {open && (
        <div className="lightbox" onClick={() => setOpen(false)}>
          <img src={props.src} alt={props.alt} />
        </div>
      )}
    </>
  );
}
