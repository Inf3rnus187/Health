import { useState } from 'react';

import type { InventoryRow, SourceStat } from '../../api/data';
import { useInventory, useReconcile } from '../../hooks/useData';
import { shortDate } from '../../utils/format';
import { usePaging } from '../Paging';
import { sourceLabel } from './sources';

function Stats({ stats }: { stats: SourceStat[] }) {
  if (stats.length === 0) {
    return <span className="muted">—</span>;
  }
  return (
    <ul className="inv-stats">
      {stats.map((stat) => (
        <li key={stat.source}>
          {sourceLabel(stat.source)} : {stat.count.toLocaleString('fr-FR')}{' '}
          <span className="muted">
            ({shortDate(stat.first)} → {shortDate(stat.last)})
          </span>
        </li>
      ))}
    </ul>
  );
}

function Row({ row }: { row: InventoryRow }) {
  return (
    <tr>
      <td>
        <strong>{row.label}</strong>
        <span className="muted inv-key">
          {row.key}
          {row.unit ? ` · ${row.unit}` : ''}
        </span>
      </td>
      <td>
        <Stats stats={row.raw} />
      </td>
      <td>
        <Stats stats={row.daily} />
      </td>
    </tr>
  );
}

function matches(row: InventoryRow, text: string): boolean {
  const needle = text.trim().toLowerCase();
  return (
    !needle ||
    row.label.toLowerCase().includes(needle) ||
    row.key.toLowerCase().includes(needle)
  );
}

function ReconcileButton() {
  const reconcile = useReconcile();
  const done = reconcile.data?.queued;
  return (
    <div className="inv-actions">
      <button
        className="btn"
        disabled={reconcile.isPending}
        onClick={() => reconcile.mutate()}
      >
        Réconcilier et recalculer les valeurs journalières
      </button>
      {done === true && <span className="muted">Lancé, mise à jour…</span>}
      {done === false && <span className="error">Worker indisponible.</span>}
    </div>
  );
}

function Table({ rows }: { rows: InventoryRow[] }) {
  const { page, bar } = usePaging(rows, 25);
  return (
    <div className="inv-scroll">
      {bar}
      <table className="inv-table">
        <thead>
          <tr>
            <th>Mesure</th>
            <th>Relevés bruts</th>
            <th>Valeurs journalières</th>
          </tr>
        </thead>
        <tbody>
          {page.map((row) => (
            <Row key={row.key} row={row} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function InventoryCard() {
  const { data, isLoading } = useInventory();
  const [text, setText] = useState('');
  const rows = (data ?? []).filter((row) => matches(row, text));
  return (
    <section className="card">
      <h2>Tout ce qui est enregistré ({rows.length})</h2>
      <p className="muted">
        Une ligne par mesure, avec chaque source. Les valeurs journalières
        (graphiques, accueil, rapports) sont recalculées à partir des relevés
        bruts avec une seule règle : Apple Santé et Health Auto Export portent
        les mêmes données, un seul des deux est compté par jour.
      </p>
      <ReconcileButton />
      <input
        className="input inv-search"
        placeholder="Filtrer (poids, glycémie, bio.…)"
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      {isLoading ? <p className="muted">Chargement…</p> : <Table rows={rows} />}
    </section>
  );
}
