import { useState } from 'react';

export function CopyButton({
  text,
  label = 'Copier',
}: {
  text: string;
  label?: string;
}) {
  const [done, setDone] = useState(false);
  const onClick = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1500);
    } catch {
      setDone(false);
    }
  };
  return (
    <button className="btn ghost" onClick={() => void onClick()}>
      {done ? 'Copié ✓' : label}
    </button>
  );
}
