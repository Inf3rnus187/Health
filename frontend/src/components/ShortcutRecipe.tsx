import { CopyButton } from './CopyButton';

const STEPS = [
  'App Raccourcis → créez un raccourci.',
  'Ajoutez « Rechercher des échantillons de santé » (Poids, Pas, FC, ' +
    'Sommeil…). Au 1er lancement, iOS demande l’accès Santé.',
  'Construisez le corps JSON (exemple ci-dessous) avec vos échantillons.',
  'Ajoutez « Obtenir le contenu de l’URL » : POST vers l’endpoint, en-tête ' +
    'Authorization: Bearer VOTRE_JETON, corps = le JSON.',
  'Lancez-le d’un clic, ou programmez une automatisation quotidienne.',
];

const SAMPLE = `{
  "date_key": "2026-09-20",
  "samples": [
    { "metric_key": "body.weight", "value": 86.2 },
    { "metric_key": "rest.hr", "value": 58 }
  ]
}`;

export function ShortcutRecipe({ endpoint }: { endpoint: string }) {
  return (
    <div className="recipe">
      <p className="muted">
        Endpoint : <code>{endpoint}</code>{' '}
        <CopyButton text={endpoint} label="Copier l’URL" />
      </p>
      <ol>
        {STEPS.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <pre className="code-block">{SAMPLE}</pre>
    </div>
  );
}
