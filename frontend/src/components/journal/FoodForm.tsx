import { type FormEvent, useState } from 'react';

import { type Food, foodPhotoPath } from '../../api/foods';
import {
  type NewPhoto,
  useDeleteFoodPhoto,
  useReadLabel,
  useSaveFood,
} from '../../hooks/useFoods';
import {
  draftOf,
  type FoodDraft,
  foodIn,
  VALUES,
  withCiqual,
  withReading,
} from './foodDraft';
import { BarcodeLookup, CiqualSearch } from './FoodSources';
import { ShotButton, ShotPreview, StoredShot } from './Shots';

type Set = (change: Partial<FoodDraft>) => void;

function Line(props: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  numeric?: boolean;
  placeholder?: string;
}) {
  return (
    <label className="field">
      {props.label}
      <input
        className="input"
        value={props.value}
        inputMode={props.numeric ? 'decimal' : undefined}
        placeholder={props.placeholder}
        onChange={(event) => props.onChange(event.target.value)}
      />
    </label>
  );
}

/** The sheet's text fields: key, label, numeric, example. */
const IDENTITY: [keyof FoodDraft, string, boolean, string?][] = [
  ['name', 'Nom', false],
  ['brand', 'Marque', false],
  ['package_g', 'Poids de la boîte / du sachet (g)', true],
  ['unit_name', 'Unité (tomate, tranche, pavé…)', false],
  ['unit_g', "Poids d'une unité (g)", true],
  [
    'aliases',
    'Autres noms dans un repas (séparés par des virgules)',
    false,
    'riz sachet, riz micro-ondes',
  ],
];

function Identity({ draft, set }: { draft: FoodDraft; set: Set }) {
  return (
    <div className="fields">
      {IDENTITY.map(([key, label, numeric, example]) => (
        <Line
          key={key}
          label={label}
          numeric={numeric}
          placeholder={example}
          value={String(draft[key])}
          onChange={(value) => set({ [key]: value })}
        />
      ))}
    </div>
  );
}

function Values({ draft, set }: { draft: FoodDraft; set: Set }) {
  return (
    <fieldset className="food-values">
      <legend>Valeurs pour 100 g</legend>
      {draft.source && <p className="muted small">Source : {draft.source}</p>}
      <div className="fields">
        {VALUES.map(([key, label]) => (
          <Line
            key={key}
            label={label}
            numeric
            value={draft.values[key]}
            onChange={(v) => set({ values: { ...draft.values, [key]: v } })}
          />
        ))}
      </div>
    </fieldset>
  );
}

function Note({ draft, set }: { draft: FoodDraft; set: Set }) {
  return (
    <label className="field">
      Note (portion habituelle, préparation…)
      <textarea
        className="input meal-text"
        rows={2}
        value={draft.note}
        placeholder="Ex. : je mange la moitié du sachet, sans beurre"
        onChange={(event) => set({ note: event.target.value })}
      />
    </label>
  );
}

function Pending(props: { photos: NewPhoto[]; onDrop: (i: number) => void }) {
  return (
    <ul className="photo-pick-chosen">
      {props.photos.map((photo, index) => (
        <li key={`${photo.file.name}-${index}`}>
          <ShotPreview file={photo.file} />
          <button
            type="button"
            className="chip-x"
            title="Retirer"
            onClick={() => props.onDrop(index)}
          >
            ×
          </button>
          <span className="muted small">
            {photo.kind === 'label' ? 'valeurs' : 'boîte'}
          </span>
        </li>
      ))}
    </ul>
  );
}

function Stored({ food }: { food: Food }) {
  const drop = useDeleteFoodPhoto();
  return (
    <ul className="photo-pick-chosen">
      {food.photos.map((photo) => (
        <li key={photo.id}>
          <StoredShot path={foodPhotoPath(food.id, photo.id)} alt="" />
          <button
            type="button"
            className="chip-x"
            title="Supprimer la photo"
            onClick={() => drop.mutate({ id: food.id, photoId: photo.id })}
          >
            ×
          </button>
        </li>
      ))}
    </ul>
  );
}

function usePhotos(onLabel: (file: File) => void) {
  const [photos, setPhotos] = useState<NewPhoto[]>([]);
  const add = (kind: NewPhoto['kind']) => (files: File[]) => {
    setPhotos((now) => [...now, ...files.map((file) => ({ file, kind }))]);
    if (kind === 'label' && files[0]) onLabel(files[0]);
  };
  const drop = (index: number) =>
    setPhotos((now) => now.filter((_, i) => i !== index));
  return { photos, add, drop };
}

type Panel = 'ciqual' | 'barcode';
const PANELS: [Panel, string][] = [
  ['ciqual', '🔎 Table Ciqual (aliment courant)'],
  ['barcode', '▥ Code-barres (Open Food Facts)'],
];

/** Fill the sheet from the Ciqual table or a barcode (one panel open). */
function Fill(props: {
  onCiqual: Parameters<typeof CiqualSearch>[0]['onPick'];
  onFound: Parameters<typeof BarcodeLookup>[0]['onFound'];
}) {
  const [open, setOpen] = useState<Panel | null>(null);
  return (
    <>
      <div className="quick">
        {PANELS.map(([panel, label]) => (
          <button
            key={panel}
            type="button"
            className="btn ghost"
            onClick={() => setOpen(open === panel ? null : panel)}
          >
            {label}
          </button>
        ))}
      </div>
      {open === 'ciqual' && <CiqualSearch onPick={props.onCiqual} />}
      {open === 'barcode' && <BarcodeLookup onFound={props.onFound} />}
    </>
  );
}

function useFill(setDraft: (next: (now: FoodDraft) => FoodDraft) => void) {
  return {
    onCiqual: (ref: Parameters<typeof withCiqual>[1]) =>
      setDraft((now) => withCiqual(now, ref)),
    onFound: (found: Parameters<typeof withReading>[1]) =>
      setDraft((now) => withReading(now, found)),
  };
}

function useFoodForm(food: Food | null, onDone: () => void) {
  const [draft, setDraft] = useState(() => draftOf(food));
  const set: Set = (change) => setDraft((now) => ({ ...now, ...change }));
  const read = useReadLabel();
  const onLabel = (file: File) =>
    read.mutate(file, {
      onSuccess: (found) => setDraft((now) => withReading(now, found)),
    });
  const shots = usePhotos(onLabel);
  const save = useSaveFood();
  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    const body = foodIn(draft);
    save.mutate(
      { id: food?.id, body, photos: shots.photos },
      { onSuccess: onDone },
    );
  };
  const fill = useFill(setDraft);
  return { draft, set, read, shots, save, onSubmit, fill };
}

function Photos(props: {
  food: Food | null;
  shots: ReturnType<typeof usePhotos>;
  reading: boolean;
}) {
  return (
    <div className="photo-pick">
      <div className="quick">
        <ShotButton
          label="🏷️ Photo des valeurs (lecture IA)"
          onPick={props.shots.add('label')}
        />
        <ShotButton
          label="📦 Photo de la boîte"
          onPick={props.shots.add('pack')}
        />
      </div>
      {props.reading && <p className="muted">Lecture de l’étiquette…</p>}
      {props.food && <Stored food={props.food} />}
      <Pending photos={props.shots.photos} onDrop={props.shots.drop} />
    </div>
  );
}

/** The sheet of a food: filled once, by hand or read from its label. */
export function FoodForm(props: { food: Food | null; onDone: () => void }) {
  const f = useFoodForm(props.food, props.onDone);
  return (
    <form className="form-box food-form" onSubmit={f.onSubmit}>
      <Photos food={props.food} shots={f.shots} reading={f.read.isPending} />
      <Fill onCiqual={f.fill.onCiqual} onFound={f.fill.onFound} />
      {f.read.isSuccess && (
        <p className="muted">Valeurs lues par l’IA : vérifiez-les.</p>
      )}
      {f.read.isError && <p className="error">{f.read.error.message}</p>}
      <Identity draft={f.draft} set={f.set} />
      <Values draft={f.draft} set={f.set} />
      <Note draft={f.draft} set={f.set} />
      <div className="row-actions">
        <button className="btn" disabled={f.save.isPending || !f.draft.name}>
          {f.save.isPending ? 'Enregistrement…' : 'Enregistrer'}
        </button>
        <button type="button" className="btn ghost" onClick={props.onDone}>
          Annuler
        </button>
      </div>
      {f.save.isError && <p className="error">{f.save.error.message}</p>}
    </form>
  );
}
