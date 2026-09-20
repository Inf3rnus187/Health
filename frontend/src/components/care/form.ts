import type { FormEvent } from 'react';

export type Submit = (event: FormEvent<HTMLFormElement>) => void;

export function formBody(form: HTMLFormElement): Record<string, string> {
  const out: Record<string, string> = {};
  new FormData(form).forEach((value, key) => {
    if (typeof value === 'string' && value.trim()) {
      out[key] = value.trim();
    }
  });
  return out;
}

export function onCreate(
  mutate: (body: Record<string, string>) => void,
): Submit {
  return (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    mutate(formBody(form));
    form.reset();
  };
}
