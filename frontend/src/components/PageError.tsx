import { Component, type ReactNode } from 'react';

const FAILED =
  'Cette page n’a pas pu se charger (le hub vient d’être mis à jour ?).';

interface State {
  failed: boolean;
}

/** A page that could not load (its code, after an update) says so. */
export class PageError extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) {
      return this.props.children;
    }
    return (
      <p className="center muted">
        {FAILED}{' '}
        <button onClick={() => window.location.reload()}>Recharger</button>
      </p>
    );
  }
}
