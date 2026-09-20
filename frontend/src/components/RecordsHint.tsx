import { useEcg, useRoutes, useWorkouts } from '../hooks/useRecords';

export function RecordsHint() {
  const workouts = useWorkouts().data ?? [];
  const ecg = useEcg().data ?? [];
  const routes = useRoutes().data ?? [];
  if (workouts.length || ecg.length || routes.length) {
    return null;
  }
  return (
    <section className="card">
      <h2>Séances, ECG et tracés GPS</h2>
      <p className="muted">
        Rien pour l’instant. Ces enregistrements viennent de l’export natif de
        l’app Santé (le zip avec « electrocardiograms » et « workout-routes ») —
        l’export CSV ne les contient pas. Importe ce zip depuis l’onglet Import
        pour les voir apparaître ici.
      </p>
    </section>
  );
}
