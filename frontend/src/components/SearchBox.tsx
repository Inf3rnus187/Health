interface SearchBoxProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function SearchBox({ value, onChange, placeholder }: SearchBoxProps) {
  return (
    <input
      className="input"
      placeholder={placeholder ?? 'Rechercher…'}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
