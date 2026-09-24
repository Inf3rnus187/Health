import { keepPreviousData, useQuery } from '@tanstack/react-query';

import {
  type Bucket,
  fetchMealSpending,
  type SpendKind,
} from '../api/spending';
import type { Range } from '../utils/range';

/** Spending on meals paid for (the previous one stays while loading). */
export function useMealSpending(range: Range, kind: SpendKind, bucket: Bucket) {
  return useQuery({
    queryKey: ['spending', range, kind, bucket],
    queryFn: () => fetchMealSpending(range, kind, bucket),
    placeholderData: keepPreviousData,
  });
}
