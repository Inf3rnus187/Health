import { useState } from 'react';

import { parse, UnsupportedDicom, type DicomImage } from '../../dicom/parse';
import { autoWindow } from '../../dicom/window';
import { DicomCanvas } from './DicomCanvas';
import { DicomControls } from './DicomControls';

interface View {
  wc: number;
  ww: number;
}

interface Setters {
  setFrames: (frames: DicomImage[]) => void;
  setIndex: (index: number) => void;
  setView: (view: View) => void;
  setError: (error: string | null) => void;
}

interface FrameProps {
  frames: DicomImage[];
  index: number;
  view: View;
  setIndex: (index: number) => void;
  setView: (view: View) => void;
}

async function loadFiles(
  files: FileList,
): Promise<{ frames: DicomImage[]; error: string | null }> {
  const frames: DicomImage[] = [];
  let error: string | null = null;
  for (const file of Array.from(files)) {
    try {
      frames.push(parse(await file.arrayBuffer()));
    } catch (err) {
      error =
        err instanceof UnsupportedDicom ? err.message : 'Fichier illisible.';
    }
  }
  frames.sort((a, b) => a.instance - b.instance);
  return { frames, error };
}

async function apply(files: FileList | null, s: Setters): Promise<void> {
  if (!files?.length) {
    return;
  }
  const { frames, error } = await loadFiles(files);
  s.setFrames(frames);
  s.setIndex(0);
  const first = frames[0];
  s.setError(first ? error : (error ?? 'Aucune image DICOM.'));
  if (first) {
    s.setView(autoWindow(first));
  }
}

function Picker({
  error,
  onFiles,
}: {
  error: string | null;
  onFiles: (files: FileList | null) => void;
}) {
  return (
    <>
      <p className="muted">
        Ouvrez les fichiers .dcm d’un CD d’imagerie (scanner, IRM, radio).
        Curseur pour parcourir les coupes, réglages de fenêtrage dessous.
        Traitement 100 % local — rien n’est envoyé au serveur.
      </p>
      <input
        className="input"
        type="file"
        accept=".dcm,application/dicom"
        multiple
        onChange={(event) => onFiles(event.target.files)}
      />
      {error && <p className="error">{error}</p>}
    </>
  );
}

function Slices({
  count,
  index,
  onIndex,
}: {
  count: number;
  index: number;
  onIndex: (index: number) => void;
}) {
  if (count <= 1) {
    return null;
  }
  return (
    <label className="dicom-slices">
      Coupe {index + 1} / {count}
      <input
        type="range"
        min={0}
        max={count - 1}
        value={index}
        onChange={(event) => onIndex(Number(event.target.value))}
      />
    </label>
  );
}

function MetaPanel({
  image,
  index,
  total,
}: {
  image: DicomImage;
  index: number;
  total: number;
}) {
  const rows: [string, string][] = [
    ...Object.entries(image.meta),
    ['Dimensions', `${image.cols} × ${image.rows}`],
    ['Coupe', `${index + 1} / ${total}`],
  ];
  return (
    <dl className="dicom-meta">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function Frame(props: FrameProps) {
  const { frames, index, view, setIndex, setView } = props;
  const image = frames[index];
  if (!image) {
    return null;
  }
  return (
    <>
      <DicomCanvas image={image} wc={view.wc} ww={view.ww} />
      <Slices count={frames.length} index={index} onIndex={setIndex} />
      <DicomControls
        wc={view.wc}
        ww={view.ww}
        onWc={(wc) => setView({ ...view, wc })}
        onWw={(ww) => setView({ ...view, ww })}
        onReset={() => setView(autoWindow(image))}
      />
      <MetaPanel image={image} index={index} total={frames.length} />
    </>
  );
}

export function DicomViewer() {
  const [frames, setFrames] = useState<DicomImage[]>([]);
  const [index, setIndex] = useState(0);
  const [view, setView] = useState<View>({ wc: 0, ww: 0 });
  const [error, setError] = useState<string | null>(null);
  const setters = { setFrames, setIndex, setView, setError };
  return (
    <section className="card">
      <h2>Visionneuse DICOM</h2>
      <Picker error={error} onFiles={(files) => void apply(files, setters)} />
      {frames.length > 0 && (
        <Frame
          frames={frames}
          index={index}
          view={view}
          setIndex={setIndex}
          setView={setView}
        />
      )}
    </section>
  );
}
