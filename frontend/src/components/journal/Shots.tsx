import { type ChangeEvent, useEffect, useState } from 'react';

import { useFileUrl } from '../../hooks/useFileUrl';
import { Zoomable } from '../Zoomable';

/** A preview of a picked file (its object URL freed when replaced). */
export function ShotPreview({ file }: { file: File }) {
  const [url, setUrl] = useState('');
  useEffect(() => {
    const made = URL.createObjectURL(file);
    setUrl(made);
    return () => URL.revokeObjectURL(made);
  }, [file]);
  return url ? <img className="photo-pick-preview" src={url} alt="" /> : null;
}

/** A stored photo (``/api/v1`` path) as a small zoomable thumbnail. */
export function StoredShot(props: { path: string; alt: string }) {
  const { url } = useFileUrl(props.path);
  return url ? <Zoomable src={url} alt={props.alt} small /> : null;
}

/** A button opening the camera or the gallery (several at once). */
export function ShotButton(props: {
  label: string;
  camera?: boolean;
  many?: boolean;
  onPick: (files: File[]) => void;
}) {
  const pick = (event: ChangeEvent<HTMLInputElement>) => {
    props.onPick([...(event.target.files ?? [])]);
    event.target.value = ''; // the same photo can be picked again
  };
  return (
    <label className="btn ghost">
      {props.label}
      <input
        type="file"
        accept="image/*"
        hidden
        multiple={props.many}
        capture={props.camera ? 'environment' : undefined}
        onChange={pick}
      />
    </label>
  );
}
