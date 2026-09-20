import { CopyButton } from './CopyButton';

const STEPS = [
  'Installe le raccourci gratuit « SimpleHealthExportCSV » (RoutineHub) : ' +
    'il exporte tes données Santé en CSV (un fichier par type), zippés.',
  'Dans son action d’envoi « Obtenir le contenu de l’URL » : Méthode ' +
    'POST, l’URL ci-dessus, et un en-tête Authorization = Bearer TON_JETON.',
  'Corps de la requête : Formulaire → un champ Fichier nommé « file » = ' +
    'le .zip. Lance-le : tout s’importe ici, comme l’upload web.',
];

export function ShortcutRecipe({ endpoint }: { endpoint: string }) {
  return (
    <div className="recipe">
      <p className="muted">
        URL d’upload : <code>{endpoint}</code>{' '}
        <CopyButton text={endpoint} label="Copier l’URL" />
      </p>
      <ol>
        {STEPS.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <p className="muted">
        Le zip contient tout (des millions de mesures, ECG, séances, tracés si
        présents) et s’importe en arrière-plan.
      </p>
    </div>
  );
}
