import { useDeleteMeasurements } from './useDeleteMeasurements';
import { useMeasurements } from './useMeasurements';
import { useMetricIndex } from './useMetricIndex';
import { useSelection } from './useSelection';

/** View-model wiring the data table, selection and bulk delete together. */
export function useDataManager() {
  const { data, isPending, isError, error } = useMeasurements();
  const metrics = useMetricIndex();
  const remove = useDeleteMeasurements();
  const { selected, toggle, clear } = useSelection();
  const rows = (data ?? []).slice().reverse();
  const onDelete = () => {
    remove.mutate([...selected]);
    clear();
  };
  return {
    rows,
    metrics,
    selected,
    toggle,
    onDelete,
    isPending,
    isError,
    error,
  };
}
