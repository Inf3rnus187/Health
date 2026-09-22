import type { HTMLAttributes, HTMLInputTypeAttribute } from 'react';

interface FieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: HTMLInputTypeAttribute;
  placeholder?: string;
  inputMode?: HTMLAttributes<HTMLInputElement>['inputMode'];
}

export function Field(props: FieldProps) {
  return (
    <>
      <label htmlFor={props.id}>{props.label}</label>
      <input
        id={props.id}
        className="input"
        type={props.type ?? 'text'}
        value={props.value}
        placeholder={props.placeholder}
        inputMode={props.inputMode}
        onChange={(event) => props.onChange(event.target.value)}
      />
    </>
  );
}
