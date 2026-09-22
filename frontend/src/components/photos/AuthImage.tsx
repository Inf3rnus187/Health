import { useEffect, useState } from 'react';

import { fetchPhotoBlob } from '../../api/photos';

export function AuthImage({ id, alt }: { id: string; alt: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    let made: string | null = null;
    fetchPhotoBlob(id)
      .then((objectUrl) => {
        made = objectUrl;
        if (active) {
          setUrl(objectUrl);
        }
      })
      .catch(() => undefined);
    return () => {
      active = false;
      if (made) {
        URL.revokeObjectURL(made);
      }
    };
  }, [id]);
  if (!url) {
    return <div className="photo-skeleton" />;
  }
  return <img className="photo-img" src={url} alt={alt} />;
}
