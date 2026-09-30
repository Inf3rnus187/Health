import { hub } from '../settings';

interface PageSizeProps {
  value: number;
  onChange: (size: number) => void;
}

/** The hub's choices (WEB_PAGE_SIZES), and the list's own size if the
 * administrator left it out: the select always shows what is used. */
function choices(value: number): number[] {
  return [...new Set([...hub().page_sizes, value])].sort((a, b) => a - b);
}

export function PageSize({ value, onChange }: PageSizeProps) {
  return (
    <label className="page-size muted">
      Par page
      <select
        className="input"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      >
        {choices(value).map((size) => (
          <option key={size} value={size}>
            {size}
          </option>
        ))}
      </select>
    </label>
  );
}
