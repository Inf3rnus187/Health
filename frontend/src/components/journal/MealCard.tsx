import { useQuery } from '@tanstack/react-query';

import { fetchMealPhoto, MEAL_TYPES, type Meal } from '../../api/journal';
import { useAnalyzeMeal, useDeleteMeal } from '../../hooks/useJournal';
import type { Selection } from '../../hooks/useSelection';
import { PickBox } from '../Bulk';
import { MealAnalysisView } from './MealAnalysisView';
import { clock } from './time';

function Photo({ meal }: { meal: Meal }) {
  const { data } = useQuery({
    queryKey: ['meal-photo', meal.id],
    queryFn: () => fetchMealPhoto(meal.id),
    enabled: meal.has_photo,
    staleTime: Infinity,
  });
  return data ? <img className="meal-photo" src={data} alt="Repas" /> : null;
}

function Reading({ meal }: { meal: Meal }) {
  const status = meal.analysis_status;
  if (status === 'queued' || status === 'running') {
    return <p className="muted">Analyse IA en cours…</p>;
  }
  if (status === 'failed') {
    return <p className="error">Analyse impossible : {meal.analysis?.error}</p>;
  }
  if (status !== 'done' || !meal.analysis) {
    return <p className="muted">Pas encore analysé.</p>;
  }
  return <MealAnalysisView a={meal.analysis} />;
}

function Actions({ meal }: { meal: Meal }) {
  const analyze = useAnalyzeMeal();
  const del = useDeleteMeal();
  const onDelete = () => {
    if (window.confirm('Supprimer ce repas et ses nutriments ?')) {
      del.mutate(meal.id);
    }
  };
  return (
    <div className="row-actions">
      <button className="btn ghost" onClick={() => analyze.mutate(meal.id)}>
        Réanalyser
      </button>
      <button className="btn ghost" onClick={onDelete}>
        Supprimer
      </button>
    </div>
  );
}

export function MealCard({ meal, sel }: { meal: Meal; sel?: Selection }) {
  return (
    <article className="meal-card">
      <Photo meal={meal} />
      <div className="meal-body">
        <h3>
          {sel && <PickBox sel={sel} id={meal.id} />}{' '}
          {MEAL_TYPES[meal.meal_type] ?? meal.meal_type} ·{' '}
          {clock(meal.eaten_at)}
        </h3>
        {meal.description && <p>{meal.description}</p>}
        {meal.price != null && <p className="muted">{meal.price} €</p>}
        <Reading meal={meal} />
        <Actions meal={meal} />
      </div>
    </article>
  );
}
