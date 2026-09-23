interface InputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}

/** A labelled input (the label is the placeholder and the title). */
export function Input(props: InputProps) {
  return (
    <input
      className="input"
      type={props.type ?? 'text'}
      aria-label={props.label}
      title={props.label}
      placeholder={props.label}
      value={props.value}
      onChange={(e) => props.onChange(e.target.value)}
    />
  );
}

/** A labelled multi-line text. */
export function Text(props: InputProps) {
  return (
    <textarea
      className="input"
      aria-label={props.label}
      placeholder={props.label}
      value={props.value}
      onChange={(e) => props.onChange(e.target.value)}
    />
  );
}

/** A select over ``{value: label}``. */
export function Choice(props: {
  options: Record<string, string>;
  value: string;
  onChange: (value: string) => void;
  name?: string;
}) {
  return (
    <select
      className="input"
      name={props.name}
      value={props.value}
      onChange={(e) => props.onChange(e.target.value)}
    >
      {Object.entries(props.options).map(([value, label]) => (
        <option key={value} value={value}>
          {label}
        </option>
      ))}
    </select>
  );
}
