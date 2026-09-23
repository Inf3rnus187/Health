import { useState } from 'react';

import { PageSize } from './PageSize';
import { Pager } from './Pager';

/** One page of a list, with its "per page" selector and pager. */
export function usePaging<T>(items: T[], initial = 10) {
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(initial);
  const start = offset < items.length ? offset : 0;
  const bar = (
    <div className="data-head">
      <PageSize
        value={limit}
        onChange={(size) => {
          setLimit(size);
          setOffset(0);
        }}
      />
      <Pager
        offset={start}
        limit={limit}
        total={items.length}
        onPage={setOffset}
      />
    </div>
  );
  return { page: items.slice(start, start + limit), bar };
}
