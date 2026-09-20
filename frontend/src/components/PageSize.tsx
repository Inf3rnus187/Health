const SIZES = [10, 25, 50, 100, 200];

interface PageSizeProps {
  value: number;
  onChange: (size: number) => void;
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
        {SIZES.map((size) => (
          <option key={size} value={size}>
            {size}
          </option>
        ))}
      </select>
    </label>
  );
}
