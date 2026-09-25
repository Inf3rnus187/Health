import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import {
  fetchMealPhoto,
  MEAL_TYPES,
  type Meal,
  mealPhotoPath,
} from '../../api/journal';
import { useAnalyzeMeal, useDeleteMeal } from '../../hooks/useJournal';
import type { Selection } from '../../hooks/useSelection';
import { frNumber } from '../../utils/format';
import { PickBox } from '../Bulk';
import { Zoomable } from '../Zoomable';
import { MealAnalysisView } from './MealAnalysisView';
import { MealEdit } from './MealEdit';
import { StoredShot } from './Shots';
import { clock } from './time';

function Photo({ meal }: { meal: Meal }) {
  const { data } = useQuery({
    queryKey: ['meal-photo', meal.id],
    queryFn: () => fetchMealPhoto(meal.id),
    enabled: meal.has_photo,
    staleTime: Infinity,
  });
  return data ? <Zoomable src={data} alt="Repas" /> : null;
}

/** The other photos: the box, the sachet, its values. */
function Extras({ meal }: { meal: Meal }) {
  if (!meal.photo_ids?.length) return null;
  return (
    <div className="meal-extras">
      {meal.photo_ids.map((id) => (
        <StoredShot key={id} path={mealPhotoPath(meal.id, id)} alt="Photo" />
      ))}
    </div>
  );
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
  return <MealAnalysisView a={meal.analysis} reference={meal.reference} />;
}

function useDelete(meal: Meal) {
  const del = useDeleteMeal();
  return () => {
    if (window.confirm('Supprimer ce repas et ses nutriments ?')) {
      del.mutate(meal.id);
    }
  };
}

interface ActionProps {
  meal: Meal;
  onReuse?: (meal: Meal) => void;
  onEdit: () => void;
}

function useButtons(props: ActionProps): [string, () => void][] {
  const { meal, onReuse } = props;
  const analyze = useAnalyzeMeal();
  const remove = useDelete(meal);
  const reuse: [string, () => void][] = onReuse
    ? [['Refaire ce repas', () => onReuse(meal)]]
    : [];
  return [
    ['Modifier', props.onEdit],
    ...reuse,
    ['Réanalyser', () => analyze.mutate(meal.id)],
    ['Supprimer', remove],
  ];
}

function Actions(props: ActionProps) {
  return (
    <div className="row-actions">
      {useButtons(props).map(([label, onClick]) => (
        <button key={label} className="btn ghost" onClick={onClick}>
          {label}
        </button>
      ))}
    </div>
  );
}

/** A meal logged from a proof (expense report, receipt, delivery). */
function FromProof({ meal }: { meal: Meal }) {
  const paid = `${frNumber(meal.price ?? 0, 2)} €`;
  return (
    <p className="muted">
      🧾 Note de frais : {paid}
      {meal.vendor && ` · ${meal.vendor}`} — la preuve est dans Travail
    </p>
  );
}

function Title({ meal, sel }: { meal: Meal; sel?: Selection }) {
  return (
    <h3>
      {sel && <PickBox sel={sel} id={meal.id} />}{' '}
      {MEAL_TYPES[meal.meal_type] ?? meal.meal_type} · {clock(meal.eaten_at)}
    </h3>
  );
}

function Body(props: {
  meal: Meal;
  sel?: Selection;
  onReuse?: (meal: Meal) => void;
  onEdit: () => void;
}) {
  const { meal } = props;
  return (
    <div className="meal-body">
      <Title meal={meal} sel={props.sel} />
      {meal.description && <p>{meal.description}</p>}
      <Extras meal={meal} />
      {meal.price != null && <FromProof meal={meal} />}
      <Reading meal={meal} />
      <Actions meal={meal} onReuse={props.onReuse} onEdit={props.onEdit} />
    </div>
  );
}

export function MealCard(props: {
  meal: Meal;
  sel?: Selection;
  onReuse?: (meal: Meal) => void;
}) {
  const [editing, setEditing] = useState(false);
  if (editing) {
    return <MealEdit meal={props.meal} onDone={() => setEditing(false)} />;
  }
  return (
    <article className="meal-card">
      <Photo meal={props.meal} />
      <Body {...props} onEdit={() => setEditing(true)} />
    </article>
  );
}
