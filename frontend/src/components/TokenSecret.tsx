import { CopyButton } from './CopyButton';

export function TokenSecret({ secret }: { secret: string }) {
  return (
    <div className="secret">
      <p className="muted">
        Jeton créé — copie-le maintenant, il ne sera plus affiché :
      </p>
      <div className="secret-row">
        <code className="secret-code">{secret}</code>
        <CopyButton text={secret} label="Copier le jeton" />
      </div>
    </div>
  );
}
