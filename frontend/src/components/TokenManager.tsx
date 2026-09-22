import { useState } from 'react';

import type { TokenCreated } from '../api/types';
import { useMintToken, useRevokeToken, useTokens } from '../hooks/useTokens';
import { CopyButton } from './CopyButton';
import { TokenList } from './TokenList';

const SCOPES: { id: string; label: string }[] = [
  { id: 'ingest:photo', label: 'Photos (miroir / appareil)' },
  { id: 'ingest:watch', label: 'Montre / Santé (sync)' },
  { id: 'write:measurements', label: 'Mesures (CSV, compteurs, Auto Export)' },
  { id: 'ingest:ppc', label: 'PPC / CPAP' },
  { id: 'write:metrics', label: 'Créer des métriques' },
  { id: 'read:all', label: 'Lecture seule' },
];

function toggle(list: string[], id: string): string[] {
  return list.includes(id) ? list.filter((x) => x !== id) : [...list, id];
}

function ScopeChecks({
  selected,
  onToggle,
}: {
  selected: string[];
  onToggle: (id: string) => void;
}) {
  return (
    <div className="scope-list">
      {SCOPES.map((scope) => (
        <label key={scope.id} className="scope-item">
          <input
            type="checkbox"
            checked={selected.includes(scope.id)}
            onChange={() => onToggle(scope.id)}
          />
          {scope.label}
        </label>
      ))}
    </div>
  );
}

function Secret({ value }: { value: string }) {
  return (
    <div className="secret">
      <p className="muted">Jeton (copiez-le, affiché une seule fois) :</p>
      <div className="secret-row">
        <code className="secret-code">{value}</code>
        <CopyButton text={value} label="Copier le jeton" />
      </div>
    </div>
  );
}

interface FormProps {
  name: string;
  scopes: string[];
  secret: string | null;
  pending: boolean;
  onName: (value: string) => void;
  onToggle: (id: string) => void;
  onCreate: () => void;
}

function CreatorForm(props: FormProps) {
  return (
    <>
      <input
        className="input"
        placeholder="Nom (ex. miroir photo)"
        value={props.name}
        onChange={(event) => props.onName(event.target.value)}
      />
      <ScopeChecks selected={props.scopes} onToggle={props.onToggle} />
      <button
        className="btn"
        disabled={props.pending || props.scopes.length === 0}
        onClick={props.onCreate}
      >
        Créer le jeton
      </button>
      {props.secret && <Secret value={props.secret} />}
    </>
  );
}

function Creator() {
  const [name, setName] = useState('');
  const [scopes, setScopes] = useState<string[]>(['ingest:photo']);
  const [secret, setSecret] = useState<string | null>(null);
  const mint = useMintToken();
  const onCreate = () =>
    mint.mutate(
      { name: name || 'jeton', scopes },
      { onSuccess: (token: TokenCreated) => setSecret(token.token) },
    );
  return (
    <CreatorForm
      name={name}
      scopes={scopes}
      secret={secret}
      pending={mint.isPending}
      onName={setName}
      onToggle={(id) => setScopes(toggle(scopes, id))}
      onCreate={onCreate}
    />
  );
}

export function TokenManager() {
  const tokens = useTokens().data ?? [];
  const revoke = useRevokeToken();
  return (
    <section className="card">
      <h2>Jetons d’accès (API)</h2>
      <p className="muted">
        Créez un jeton et cochez ce qu’il peut faire (Photos, Santé, Mesures…).
        Le secret ne s’affiche qu’une fois — copiez-le et collez-le dans votre
        appareil (ex. `MORNING_PHOTO_TOKEN`).
      </p>
      <Creator />
      <TokenList tokens={tokens} onRevoke={(id) => revoke.mutate(id)} />
    </section>
  );
}
