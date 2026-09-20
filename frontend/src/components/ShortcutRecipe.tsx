const STEPS = [
  'Installe le raccourci gratuit « SimpleHealthExportCSV » (RoutineHub) : ' +
    'il exporte tes données Santé en CSV (un fichier par type), zippés.',
  'Dans son action d’envoi « Obtenir le contenu de l’URL » : Méthode ' +
    'POST, et colle l’URL d’upload ci-dessus (le jeton est dedans).',
  'Corps de la requête : Formulaire → un champ Fichier nommé « file » = ' +
    'le .zip. Lance-le : tout s’importe ici, comme l’upload web.',
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
        Aucun en-tête « Authorization » à saisir : le jeton est déjà dans l’URL.
        Le zip contient tout et s’importe en arrière-plan.
      </p>
    </div>
  );
}
