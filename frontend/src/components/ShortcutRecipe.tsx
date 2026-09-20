const STEPS = [
  'Ouvre le fichier téléchargé sur ton iPhone : il s’ouvre dans ' +
    'l’app Raccourcis.',
  'Une seule fois : Réglages → Raccourcis → active « Autoriser les ' +
    'raccourcis non fiables », puis rouvre le fichier et ajoute-le.',
  'Lance-le : saisis ton poids, il part vers ton serveur. Aucun jeton ' +
    'ni JSON à toucher — tout est déjà inclus.',
];

export function ShortcutRecipe() {
  return (
    <div className="recipe">
      <ol>
        {STEPS.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <p className="muted">
        L’historique complet (millions de mesures, ECG, séances, tracés)
        s’importe en un fichier via l’onglet Import (export Santé .zip) — sans
        rien sélectionner non plus.
      </p>
    </div>
  );
}
