import type { WorkStats } from '../../api/work';
import { shortDate } from '../../utils/format';
import { hm } from './format';

type Tile = [string, string, string?];

function tiles(stats: WorkStats): Tile[] {
  const longest = stats.longest_day;
  return [
    ['Heures travaillées', hm(stats.total_hours)],
    ['Jours travaillés', String(stats.days_worked)],
    ['Moyenne par jour', hm(stats.avg_day_hours)],
    [
      'Moyenne par semaine complète',
      hm(stats.avg_week_hours),
      `${stats.full_weeks} semaines sans absence ni férié`,
    ],
    ['Embauche moyenne', stats.avg_start ?? '—'],
    ['Débauche moyenne', stats.avg_end ?? '—'],
    ['Heures sup', hm(stats.overtime_hours), 'au-delà du contrat, légal'],
    [
      'Au-delà de l’objectif',
      hm(stats.beyond_target_hours),
      'contrat moins les jours d’absence',
    ],
    ['Jours > 10 h', String(stats.days_over_10h)],
    ['Semaines > 48 h', String(stats.weeks_over_48h)],
    ['Plus longue journée', longest ? hm(longest.hours) : '—'],
    ...remoteTiles(stats).concat(offTiles(stats)),
  ];
}

function remoteTiles(stats: WorkStats): Tile[] {
  if (!stats.remote_hours) return [];
  const after = stats.remote_after_site.length;
  return [
    [
      'Dont à distance',
      hm(stats.remote_hours),
      `${stats.remote_days} jours, dont ${after} en plus du sur place`,
    ],
  ];
}

function offTiles(stats: WorkStats): Tile[] {
  const off: Tile[] = stats.absences.map((a) => [
    a.label,
    `${a.days} j`,
    `${a.workdays} jours ouvrés`,
  ]);
  const during = stats.worked_while_off;
  if (during.length > 0) {
    off.push([
      'Travaillé pendant une absence',
      `${during.length} j`,
      during.map((d) => shortDate(d.date)).join(', '),
    ]);
  }
  return off;
}

/** The headline numbers of the period, days off included. */
export function StatsTiles({ stats }: { stats: WorkStats }) {
  return (
    <div className="tiles">
      {tiles(stats).map(([label, value, hint]) => (
        <div key={label} className="tile">
          <span className="tile-label muted">{label}</span>
          <span className="tile-value">{value}</span>
          {hint && <span className="tile-date muted">{hint}</span>}
        </div>
      ))}
    </div>
  );
}

const HEAD = [
  'Période',
  'Heures',
  'Dont distance',
  'Jours',
  'Absences (j)',
  'Moy. / semaine présente',
  'Heures sup',
];

function cells(p: WorkStats['periods'][number]): string[] {
  return [
    p.label,
    hm(p.total_hours),
    p.remote_hours ? hm(p.remote_hours) : '—',
    String(p.days_worked),
    String(p.absent_days),
    hm(p.week_average),
    hm(p.overtime_hours),
  ];
}

/** Short / medium / long term: 7 days, 30 days, 3 months, 1 year. */
export function PeriodsTable({ stats }: { stats: WorkStats }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {HEAD.map((title) => (
              <th key={title}>{title}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {stats.periods.map((p) => (
            <tr key={p.label}>
              {cells(p).map((cell, index) => (
                <td key={index}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
