import { type FormEvent, useState } from 'react';

import type { FoodPortion } from '../../api/foods';
import { MEAL_TYPES } from '../../api/journal';
import { useCreateMeal } from '../../hooks/useJournal';
import { FoodPick } from './FoodPick';
import { PhotoPick } from './PhotoPick';
import { mealOfNow, nowLocal } from './time';

/** A past meal to log again (« Refaire ce repas »). */
export interface MealDraft {
  meal_type: string;
  description: string;
  foods: FoodPortion[];
}

const HINT =
  'Ex. : 2 tomates, ½ concombre, comté dans la salade, un filet de blanc ' +
  'de poulet, pommes de terre rissolées — sans huile, beurre ni sauce.';

function When({ kind }: { kind: string }) {
  return (
    <>
      <select className="input" name="meal_type" defaultValue={kind}>
        {Object.entries(MEAL_TYPES).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <input
        className="input"
        type="datetime-local"
        name="eaten_at"
        defaultValue={nowLocal()}
      />
    </>
  );
}

function What({ text }: { text: string }) {
  return (
    <textarea
      className="input meal-text"
      name="description"
      rows={3}
      defaultValue={text}
      placeholder={HINT}
    />
  );
}

function Help() {
  return (
    <>
      <p className="muted">
        Décrivez ce que vous avez mangé (quantités, cuisson, sans matière
        grasse…) : la description fait foi, les photos aident à estimer les
        portions et à lire les étiquettes. L’analyse IA prend une à quelques
        minutes.
      </p>
      <p className="muted">
        Suivi santé seulement (diabète, foie, poids…) : un repas noté ici n’est
        jamais une preuve de travail et n’a pas de prix. Une note de frais, un
        reçu ou une livraison s’ajoute comme preuve dans Travail › Dossier
        travail et santé : son repas arrive alors ici aussi.
      </p>
    </>
  );
}

/** The form's data: the plate first (``file``), the other photos, foods. */
function formData(form: HTMLFormElement, photos: File[], foods: FoodPortion[]) {
  const data = new FormData(form);
  photos.forEach((photo, i) => data.append(i ? 'photos' : 'file', photo));
  if (foods.length) data.set('foods', JSON.stringify(foods));
  return data;
}

function useSend(draft: MealDraft | null) {
  const create = useCreateMeal();
  const [photos, setPhotos] = useState<File[]>([]);
  const [foods, setFoods] = useState<FoodPortion[]>(draft?.foods ?? []);
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const done = () => {
      form.reset();
      setPhotos([]);
      setFoods([]);
    };
    create.mutate(formData(form, photos, foods), { onSuccess: done });
  };
  return { create, photos, setPhotos, foods, setFoods, onSubmit };
}

/** Log a meal: type, time, what was eaten, photos, foods → AI reading. */
export function MealForm({ draft }: { draft: MealDraft | null }) {
  const s = useSend(draft);
  return (
    <section className="card" id="meal-form">
      <h2>Ajouter un repas (suivi santé)</h2>
      <form className="meal-form" onSubmit={s.onSubmit}>
        <When kind={draft?.meal_type ?? mealOfNow()} />
        <What text={draft?.description ?? ''} />
        <FoodPick value={s.foods} onChange={s.setFoods} />
        <PhotoPick photos={s.photos} onChange={s.setPhotos} />
        <button className="btn" disabled={s.create.isPending}>
          {s.create.isPending ? 'Envoi…' : 'Enregistrer et analyser'}
        </button>
      </form>
      {s.create.isError && <p className="error">{s.create.error.message}</p>}
      <Help />
    </section>
  );
}
