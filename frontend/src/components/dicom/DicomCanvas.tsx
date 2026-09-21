import { useEffect, useRef } from 'react';

import type { DicomImage } from '../../dicom/parse';
import { toImageData } from '../../dicom/window';

export function DicomCanvas({
  image,
  wc,
  ww,
}: {
  image: DicomImage;
  wc: number;
  ww: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx || !image.rows || !image.cols) {
      return;
    }
    canvas.width = image.cols;
    canvas.height = image.rows;
    ctx.putImageData(toImageData(image, wc, ww), 0, 0);
  }, [image, wc, ww]);
  return <canvas ref={ref} className="dicom-canvas" />;
}
