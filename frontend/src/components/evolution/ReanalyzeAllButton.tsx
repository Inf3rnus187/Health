import { useReanalyzeAll } from '../../hooks/useEvolution';

const CONFIRM =
  'Réanalyser toutes les photos avec la méthode v2 ? L’opération tourne ' +
  'en arrière-plan et peut prendre plusieurs minutes.';

function queuedText(queued: number): string {
  if (queued === 0) {
    return 'Aucune photo à analyser.';
  }
  const noun = queued > 1 ? 'photos' : 'photo';
  return (
    `${queued} ${noun} en file d’analyse… ` +
    'Les résultats apparaissent au fur et à mesure.'
  );
}

interface FeedbackProps {
  queued?: number;
  error: Error | null;
}

function Feedback({ queued, error }: FeedbackProps) {
  if (error) {
    return <p className="error">Erreur : {error.message}</p>;
  }
  if (queued === undefined) {
    return null;
  }
  return <p className="muted">{queuedText(queued)}</p>;
}

export function ReanalyzeAllButton() {
  const mutation = useReanalyzeAll();
  const onClick = () => {
    if (window.confirm(CONFIRM)) {
      mutation.mutate();
    }
  };
  return (
    <div className="reanalyze-all">
      <button
        className="btn btn-ghost"
        type="button"
        disabled={mutation.isPending}
        onClick={onClick}
      >
        {mutation.isPending
          ? 'Mise en file…'
          : 'Réanalyser tout l’historique (méthode v2)'}
      </button>
      <Feedback queued={mutation.data?.queued} error={mutation.error} />
    </div>
  );
}
