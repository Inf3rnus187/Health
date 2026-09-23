import type { ReactNode } from 'react';

import { usePaging } from './Paging';

/** A table, a page at a time: the pager bar, then the page's rows. */
export function PagedRows<T>(props: {
  items: T[];
  row: (item: T) => ReactNode;
}) {
  const { page, bar } = usePaging(props.items);
  return (
    <>
      {bar}
      <div className="table-wrap">
        <table className="data-table">
          <tbody>{page.map(props.row)}</tbody>
        </table>
      </div>
    </>
  );
}
