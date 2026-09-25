import { useMutation } from '@tanstack/react-query';

import { type ScanResult, scanBarcode } from '../../api/foods';
import { ShotButton } from './Shots';

/** Scan a barcode: the camera, or a photo from the gallery. */
export function BarcodeScan(props: { onResult: (r: ScanResult) => void }) {
  const scan = useMutation({ mutationFn: scanBarcode });
  const pick = (files: File[]) => {
    if (files[0]) scan.mutate(files[0], { onSuccess: props.onResult });
  };
  return (
    <>
      <div className="quick">
        <ShotButton label="📷 Scanner le code-barres" camera onPick={pick} />
        <ShotButton label="🖼️ Photo du code-barres" onPick={pick} />
      </div>
      {scan.isPending && <p className="muted">Lecture du code-barres…</p>}
      {scan.isError && <p className="error">{scan.error.message}</p>}
    </>
  );
}
