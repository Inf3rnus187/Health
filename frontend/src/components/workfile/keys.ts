/** What a Shortcut history file counts (same keys as ``/sync/tally``). */
export const LOG_KEYS: Record<string, string> = {
  'work.start': 'Embauches',
  'work.end': 'Débauches',
  'habit.cigarettes': 'Cigarettes',
  'habit.coffee': 'Cafés',
  'water.bottles_1_5': 'Bouteilles d’eau',
  'elimination.urination': 'Pipi',
  'habit.urges_broken': 'Envies cassées',
};

const NAME_KEYS: [string[], string][] = [
  [['debauche', 'depart', 'sortie'], 'work.end'],
  [['embauche', 'arrivee', 'entree'], 'work.start'],
  [['pipi', 'urin', 'miction'], 'elimination.urination'],
  [['cigarette', 'clope', 'tabac'], 'habit.cigarettes'],
  [['envie'], 'habit.urges_broken'],
  [['cafe', 'coffee'], 'habit.coffee'],
  [['eau', 'water', 'bouteille'], 'water.bottles_1_5'],
];

/** The key a file name points to ('' when it says nothing). */
export function keyFor(name: string): string {
  const plain = name.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const hit = NAME_KEYS.find(([words]) => words.some((w) => plain.includes(w)));
  return hit ? hit[1] : '';
}

/** Minutes as ``7 h 05``. */
export function hoursText(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined) {
    return '—';
  }
  const m = Math.round(minutes);
  return `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')}`;
}
