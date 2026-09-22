import type { Marker, MarkerInput, MarkerLevel } from '../../api/evolution';
import { useMarkers } from '../../hooks/useEvolution';
import { frNumber, shortDate } from '../../utils/format';
import { ProfileForm } from './ProfileForm';

const LEVEL_LABEL: Record<MarkerLevel, string> = {
  ok: 'Normal',
  warn: 'À surveiller',
  high: 'Élevé',
  missing: 'Incomplet',
  info: 'Info',
};

function formatValue(marker: Marker): string {
  if (marker.value === null) {
    return '—';
  }
  const num = frNumber(marker.value, 2);
  return marker.unit ? `${num} ${marker.unit}` : num;
}

function inputText(input: MarkerInput): string {
  const unit = input.unit ? ` ${input.unit}` : '';
  const when = input.date ? ` (${shortDate(input.date)})` : '';
  return `${input.label} ${frNumber(input.value, 2)}${unit}${when}`;
}

/** The exact values fed into the formula, so every number is traceable. */
function MarkerInputs({ inputs }: { inputs?: MarkerInput[] }) {
  if (!inputs || inputs.length === 0) {
    return null;
  }
  return (
    <span className="marker-small marker-inputs">
      Valeurs utilisées : {inputs.map(inputText).join(' · ')}
    </span>
  );
}

function MarkerFoot({ marker }: { marker: Marker }) {
  const missing = marker.missing ?? [];
  return (
    <>
      {marker.date && (
        <span className="marker-small muted">Le {shortDate(marker.date)}</span>
      )}
      {missing.length > 0 && (
        <span className="marker-missing">Manque : {missing.join(', ')}</span>
      )}
    </>
  );
}

function MarkerItem({ marker }: { marker: Marker }) {
  return (
    <li className="marker">
      <div className="marker-head">
        <span className="marker-label">{marker.label}</span>
        <span className={`badge lvl lvl-${marker.level}`}>
          {LEVEL_LABEL[marker.level] ?? marker.level}
        </span>
      </div>
      <span className="marker-value">{formatValue(marker)}</span>
      {marker.interpretation && <span>{marker.interpretation}</span>}
      <MarkerInputs inputs={marker.inputs} />
      {marker.reference && (
        <span className="marker-small muted">{marker.reference}</span>
      )}
      <MarkerFoot marker={marker} />
    </li>
  );
}

interface ListProps {
  markers?: Marker[];
  loading: boolean;
  error: Error | null;
}

function MarkerList({ markers, loading, error }: ListProps) {
  if (loading) {
    return <p className="muted">Chargement…</p>;
  }
  if (error || !markers) {
    const why = error ? ` : ${error.message}` : '';
    return <p className="error">Marqueurs indisponibles{why}.</p>;
  }
  return (
    <ul className="marker-grid">
      {markers.map((marker) => (
        <MarkerItem key={marker.key} marker={marker} />
      ))}
    </ul>
  );
}

export function MarkersCard() {
  const { data, isLoading, error } = useMarkers();
  return (
    <section className="card">
      <h2>Marqueurs cliniques validés</h2>
      <ProfileForm profile={data?.profile} />
      <MarkerList markers={data?.markers} loading={isLoading} error={error} />
      <p className="disclaimer">
        Indicateurs de dépistage validés, pas un diagnostic : la stéatose se
        confirme par échographie / FibroScan et le diabète par HbA1c ou glycémie
        à jeun contrôlées — à discuter avec votre médecin.
      </p>
    </section>
  );
}
