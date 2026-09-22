import type { ApiToken } from '../api/types';
import { shortDateTime } from '../utils/datetime';

interface TokenListProps {
  tokens: ApiToken[];
  onRevoke: (id: string) => void;
}

export function TokenList({ tokens, onRevoke }: TokenListProps) {
  const active = tokens.filter((token) => !token.revoked);
  if (active.length === 0) {
    return null;
  }
  return (
    <ul className="token-list">
      {active.map((token) => (
        <li key={token.id}>
          <span className="import-name">{token.name}</span>
          <span className="muted">{token.scopes.join(', ')}</span>
          <span className="muted">{shortDateTime(token.created_at)}</span>
          <button className="btn ghost" onClick={() => onRevoke(token.id)}>
            Révoquer
          </button>
        </li>
      ))}
    </ul>
  );
}
