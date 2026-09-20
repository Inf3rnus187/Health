import { useDataManager } from '../hooks/useDataManager';
import { DataPanel } from './DataPanel';

export function DataManager() {
  const view = useDataManager();
  if (view.isError) {
    return <p className="error">Erreur : {(view.error as Error).message}</p>;
  }
  if (view.isPending) {
    return <p className="muted">Chargement…</p>;
  }
  return (
    <DataPanel
      rows={view.rows}
      metrics={view.metrics}
      selected={view.selected}
      onToggle={view.toggle}
      onDelete={view.onDelete}
    />
  );
}
