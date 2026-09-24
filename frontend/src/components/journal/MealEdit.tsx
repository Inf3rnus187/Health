import { useQuery } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';

import type { FoodPortion } from '../../api/foods';
import {
  fetchMealPhoto,
  MEAL_TYPES,
  type Meal,
  mealPhotoPath,
} from '../../api/journal';
import { useEditMeal } from '../../hooks/useJournal';
import { Zoomable } from '../Zoomable';
import { FoodPick } from './FoodPick';
import { ShotButton, ShotPreview, StoredShot } from './Shots';
import { localInput } from './time';

function Drop(props: { onClick: () => void }) {
  return (
    <button
      type="button"
      className="chip-x"
      title="Retirer"
      onClick={props.onClick}
    >
      ×
    </button>
  );
}

function Plate(props: { meal: Meal; onDrop: () => void }) {
  const { data } = useQuery({
    queryKey: ['meal-photo', props.meal.id],
    queryFn: () => fetchMealPhoto(props.meal.id),
    staleTime: Infinity,
  });
  if (!data) return null;
  return (
    <li>
      <Zoomable src={data} alt="Assiette" small />
      <Drop onClick={props.onDrop} />
    </li>
  );
}

interface Photos {
  plate: boolean;
  kept: string[];
  add: File[];
}

function Kept(props: { path: string; onDrop: () => void }) {
  return (
    <li>
      <StoredShot path={props.path} alt="Photo" />
      <Drop onClick={props.onDrop} />
    </li>
  );
}

function Pending(props: { file: File; onDrop: () => void }) {
  return (
    <li>
      <ShotPreview file={props.file} />
      <Drop onClick={props.onDrop} />
    </li>
  );
}

/** Take a photo out of the edit (removed when saved). */
function dropper(photos: Photos, set: (p: Photos) => void) {
  return {
    plate: () => set({ ...photos, plate: false }),
    kept: (id: string) =>
      set({ ...photos, kept: photos.kept.filter((k) => k !== id) }),
    added: (i: number) =>
      set({ ...photos, add: photos.add.filter((_, j) => j !== i) }),
  };
}

interface ListProps {
  meal: Meal;
  photos: Photos;
  set: (p: Photos) => void;
}

/** The photos kept and the ones added, each with its ×. */
function Items({ meal, photos, set }: ListProps) {
  const drop = dropper(photos, set);
  return (
    <>
      {photos.kept.map((id) => (
        <Kept
          key={id}
          path={mealPhotoPath(meal.id, id)}
          onDrop={() => drop.kept(id)}
        />
      ))}
      {photos.add.map((file, i) => (
        <Pending key={i} file={file} onDrop={() => drop.added(i)} />
      ))}
    </>
  );
}

function PhotoList(props: ListProps) {
  const { meal, photos } = props;
  return (
    <ul className="photo-pick-chosen">
      {meal.has_photo && photos.plate && (
        <Plate meal={meal} onDrop={dropper(photos, props.set).plate} />
      )}
      <Items {...props} />
    </ul>
  );
}

function PhotoEdit(props: {
  meal: Meal;
  photos: Photos;
  set: (p: Photos) => void;
}) {
  const add = (files: File[]) =>
    props.set({ ...props.photos, add: [...props.photos.add, ...files] });
  return (
    <div className="photo-pick">
      <span className="muted">
        Photos (sans photo d’assiette, la première ajoutée le devient)
      </span>
      <div className="quick">
        <ShotButton label="📷 Prendre une photo" camera onPick={add} />
        <ShotButton label="🖼️ Galerie" many onPick={add} />
      </div>
      <PhotoList {...props} />
    </div>
  );
}

function useMealEdit(meal: Meal, onDone: () => void) {
  const [kind, setKind] = useState(meal.meal_type);
  const [at, setAt] = useState(localInput(meal.eaten_at));
  const [text, setText] = useState(meal.description);
  const [foods, setFoods] = useState<FoodPortion[]>(meal.foods ?? []);
  const [photos, setPhotos] = useState<Photos>({
    plate: true,
    kept: meal.photo_ids ?? [],
    add: [],
  });
  const save = useEditMeal();
  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    const dropIds = (meal.photo_ids ?? []).filter(
      (id) => !photos.kept.includes(id),
    );
    const change = { meal_type: kind, eaten_at: at, description: text, foods };
    const dropPlate = meal.has_photo && !photos.plate;
    const edit = { id: meal.id, change, dropPlate, dropIds, add: photos.add };
    save.mutate(edit, { onSuccess: onDone });
  };
  const fields = { kind, setKind, at, setAt, text, setText, foods, setFoods };
  return { fields, photos, setPhotos, save, onSubmit };
}

type Form = ReturnType<typeof useMealEdit>['fields'];

function When({ f }: { f: Form }) {
  return (
    <>
      <select
        className="input"
        value={f.kind}
        onChange={(e) => f.setKind(e.target.value)}
      >
        {Object.entries(MEAL_TYPES).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <input
        className="input"
        type="datetime-local"
        value={f.at}
        onChange={(e) => f.setAt(e.target.value)}
      />
    </>
  );
}

function Fields({ f }: { f: Form }) {
  return (
    <>
      <When f={f} />
      <textarea
        className="input meal-text"
        rows={3}
        value={f.text}
        onChange={(e) => f.setText(e.target.value)}
      />
      <FoodPick value={f.foods} onChange={f.setFoods} />
    </>
  );
}

/** Change a meal afterwards; saving reads it again (once). */
export function MealEdit(props: { meal: Meal; onDone: () => void }) {
  const e = useMealEdit(props.meal, props.onDone);
  return (
    <form className="meal-form form-box" onSubmit={e.onSubmit}>
      <Fields f={e.fields} />
      <PhotoEdit meal={props.meal} photos={e.photos} set={e.setPhotos} />
      <div className="row-actions">
        <button className="btn" disabled={e.save.isPending}>
          {e.save.isPending ? 'Enregistrement…' : 'Enregistrer et réanalyser'}
        </button>
        <button type="button" className="btn ghost" onClick={props.onDone}>
          Annuler
        </button>
      </div>
      {e.save.isError && <p className="error">{e.save.error.message}</p>}
    </form>
  );
}
