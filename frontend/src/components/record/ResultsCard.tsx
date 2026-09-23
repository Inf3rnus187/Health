import { useState } from 'react';
import { Link } from 'react-router-dom';

import type { RecordResult, ResultPoint } from '../../api/record';
import { useRecord } from '../../hooks/useRecord';
import { colorForMetric } from '../../theme/palette';
import { frNumber, shortDate, signed } from '../../utils/format';
import { Sparkline } from '../Sparkline';
import { DocLink } from './DocLink';

function value(point: ResultPoint, unit: string | null): string {
  return `${frNumber(point.value, 2)}${unit ? ` ${unit}` : ''}`;
}

function Previous({ result }: { result: RecordResult }) {
  const prev = result.previous;
  if (!prev || result.change === null) {
    return <span className="muted">—</span>;
  }
  return (
    <>
      {value(prev, result.unit)}{' '}
      <span className="muted">({shortDate(prev.date)})</span>
      <br />
      <strong>{signed(result.change, 2)}</strong>
    </>
  );
}

function Row({ result }: { result: RecordResult }) {
  const doc = result.latest.document;
  return (
    <tr>
      <td>
        <Link to={`/donnees?metric=${encodeURIComponent(result.key)}`}>
          {result.label}
        </Link>
        <Sparkline
          values={result.history.map((h) => h.value)}
          color={colorForMetric(result.key)}
        />
      </td>
      <td>
        <strong>{value(result.latest, result.unit)}</strong>
        <br />
        <span className="muted">{shortDate(result.latest.date)}</span>
      </td>
      <td>
        <Previous result={result} />
      </td>
      <td>{doc ? <DocLink doc={doc} /> : <span className="muted">—</span>}</td>
    </tr>
  );
}

function matches(result: RecordResult, text: string): boolean {
  const needle = text.trim().toLowerCase();
  return (
    !needle ||
    result.label.toLowerCase().includes(needle) ||
    result.key.includes(needle)
  );
}

function Table({ rows }: { rows: RecordResult[] }) {
  return (
    <div className="inv-scroll">
      <table className="inv-table">
        <thead>
          <tr>
            <th>Analyse</th>
            <th>Dernier résultat</th>
            <th>Précédent · évolution</th>
            <th>Document</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <Row key={row.key} result={row} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Every lab / FibroScan result with its history and source document. */
export function ResultsCard() {
  const [search, setSearch] = useState('');
  const results = useRecord().data?.results ?? [];
  if (results.length === 0) {
    return null;
  }
  return (
    <section className="card">
      <h2>Résultats d’examens</h2>
      <p className="muted">
        Biologie et FibroScan, toutes sources (PDF, IA vérifiée, saisie) — les
        mêmes valeurs que les marqueurs, les graphiques et les rapports.
      </p>
      <input
        className="input"
        placeholder="Filtrer (ex. ALAT, HbA1c)"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <Table rows={results.filter((r) => matches(r, search))} />
    </section>
  );
}
