import { BeforeAfter } from './BeforeAfter';
import { MarkersCard } from './MarkersCard';
import { ProtocolCard } from './ProtocolCard';
import { ReanalyzeAllButton } from './ReanalyzeAllButton';
import { TrendCard } from './TrendCard';
import { WeightCard } from './WeightCard';

function MethodCard() {
  return (
    <section className="card">
      <h2>Méthode d’analyse</h2>
      <p className="muted method-text">
        Contrôle qualité automatique de chaque photo, scores 0–10 à l’aveugle
        par angle sur des grilles ancrées, puis comparaisons appariées (ordre
        contrebalancé) avec la référence, J-7, J-30 et J-90.
      </p>
      <ReanalyzeAllButton />
    </section>
  );
}

export function EvolutionView() {
  return (
    <>
      <ProtocolCard />
      <MarkersCard />
      <WeightCard />
      <TrendCard />
      <BeforeAfter />
      <MethodCard />
    </>
  );
}
