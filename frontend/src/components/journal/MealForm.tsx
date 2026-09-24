import { type FormEvent, useState } from 'react';

import { MEAL_TYPES } from '../../api/journal';
import { useCreateMeal } from '../../hooks/useJournal';
import { PhotoPick } from './PhotoPick';
import { mealOfNow, nowLocal } from './time';

const HINT =
  'Ex. : 2 tomates, ½ concombre, comté dans la salade, un filet de blanc ' +
  'de poulet, pommes de terre rissolées — sans huile, beurre ni sauce.';

function When() {
  return (
    <>
      <select className="input" name="meal_type" defaultValue={mealOfNow()}>
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

function What() {
  return (
    <textarea
      className="input meal-text"
      name="description"
      rows={3}
      placeholder={HINT}
    />
  );
}

function Help() {
  return (
    <>
      <p className="muted">
        Décrivez ce que vous avez mangé (quantités, cuisson, sans matière
        grasse…) : la description fait foi, la photo aide à estimer les
        portions. L’analyse IA prend une à quelques minutes.
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

/** Send the form with the photo picked (camera and gallery: one photo). */
function useSend() {
  const create = useCreateMeal();
  const [photo, setPhoto] = useState<File | null>(null);
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    if (photo) data.set('file', photo);
    const done = () => {
      form.reset();
      setPhoto(null);
    };
    create.mutate(data, { onSuccess: done });
  };
  return { create, photo, setPhoto, onSubmit };
}

/** Log a meal: type, time, what was eaten, photo → AI reading. */
export function MealForm() {
  const { create, photo, setPhoto, onSubmit } = useSend();
  return (
    <section className="card">
      <h2>Ajouter un repas (suivi santé)</h2>
      <form className="meal-form" onSubmit={onSubmit}>
        <When />
        <What />
        <PhotoPick photo={photo} onPick={setPhoto} />
        <button className="btn" disabled={create.isPending}>
          {create.isPending ? 'Envoi…' : 'Enregistrer et analyser'}
        </button>
      </form>
      {create.isError && <p className="error">{create.error.message}</p>}
      <Help />
    </section>
  );
}
