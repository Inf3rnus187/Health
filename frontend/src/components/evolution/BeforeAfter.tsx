import type { AngleTrend, DatedPhoto } from '../../api/evolution';
import { useTrend } from '../../hooks/useEvolution';
import { frNumber, shortDate } from '../../utils/format';
import { AuthImage } from '../photos/AuthImage';
import { angleLabel } from '../photos/labels';

interface Pair {
  angle: string;
  baseline: DatedPhoto;
  latest: DatedPhoto;
}

/** Angles with two distinct photos (reference and latest) to compare. */
function pairsOf(angles: AngleTrend[]): Pair[] {
  const out: Pair[] = [];
  for (const { angle, baseline, latest } of angles) {
    if (baseline && latest && baseline.photo_id !== latest.photo_id) {
      out.push({ angle, baseline, latest });
    }
  }
  return out;
}

function Shot({ photo, caption }: { photo: DatedPhoto; caption: string }) {
  const kg = photo.weight == null ? '' : ` · ${frNumber(photo.weight)} kg`;
  const text = `${caption} ${shortDate(photo.date)}${kg}`;
  return (
    <figure className="ba-shot">
      <AuthImage id={photo.photo_id} alt={text} />
      <figcaption>{text}</figcaption>
    </figure>
  );
}

function PairView({ pair }: { pair: Pair }) {
  return (
    <div className="ba-angle">
      <h3>{angleLabel(pair.angle)}</h3>
      <div className="ba-pair">
        <Shot photo={pair.baseline} caption="Référence" />
        <Shot photo={pair.latest} caption="Dernière" />
      </div>
    </div>
  );
}

function Pairs({ pairs }: { pairs: Pair[] }) {
  if (pairs.length === 0) {
    return (
      <p className="muted">
        Il faut au moins deux photos valides d’un même angle pour comparer.
      </p>
    );
  }
  return (
    <div className="ba-grid">
      {pairs.map((pair) => (
        <PairView key={pair.angle} pair={pair} />
      ))}
    </div>
  );
}

export function BeforeAfter() {
  const { data, isLoading } = useTrend();
  return (
    <section className="card">
      <h2>Avant / après</h2>
      {isLoading ? (
        <p className="muted">Chargement…</p>
      ) : (
        <Pairs pairs={pairsOf(data?.angles ?? [])} />
      )}
    </section>
  );
}
