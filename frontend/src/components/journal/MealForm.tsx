import type { FormEvent } from 'react';

import { MEAL_TYPES } from '../../api/journal';
import { useCreateMeal } from '../../hooks/useJournal';
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
    <>
      <textarea
        className="input meal-text"
        name="description"
        rows={3}
        placeholder={HINT}
      />
      <label className="meal-file">
        Photo du repas (facultative)
        <input type="file" name="file" accept="image/*" capture="environment" />
      </label>
    </>
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

/** Log a meal: type, time, what was eaten, photo → AI reading. */
export function MealForm() {
  const create = useCreateMeal();
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    create.mutate(new FormData(form), { onSuccess: () => form.reset() });
  };
  return (
    <section className="card">
      <h2>Ajouter un repas (suivi santé)</h2>
      <form className="meal-form" onSubmit={onSubmit}>
        <When />
        <What />
        <button className="btn" disabled={create.isPending}>
          {create.isPending ? 'Envoi…' : 'Enregistrer et analyser'}
        </button>
      </form>
      {create.isError && <p className="error">{create.error.message}</p>}
      <Help />
    </section>
  );
}
