import type { WorkStats } from '../../api/work';
import { hm } from './format';

function tiles(stats: WorkStats): [string, string][] {
  const longest = stats.longest_day;
  return [
    ['Heures travaillées', hm(stats.total_hours)],
    ['Jours travaillés', String(stats.days_worked)],
    ['Moyenne par jour', hm(stats.avg_day_hours)],
    ['Moyenne par semaine', hm(stats.avg_week_hours)],
    ['Embauche moyenne', stats.avg_start ?? '—'],
    ['Débauche moyenne', stats.avg_end ?? '—'],
    ['Heures sup', hm(stats.overtime_hours)],
    ['Jours > 10 h', String(stats.days_over_10h)],
    ['Semaines > 48 h', String(stats.weeks_over_48h)],
    ['Plus longue journée', longest ? hm(longest.hours) : '—'],
  ];
}

/** The headline numbers of the period. */
export function StatsTiles({ stats }: { stats: WorkStats }) {
  return (
    <div className="tiles">
      {tiles(stats).map(([label, value]) => (
        <div key={label} className="tile">
          <span className="tile-label muted">{label}</span>
          <span className="tile-value">{value}</span>
        </div>
      ))}
    </div>
  );
}

const HEAD = ['Période', 'Heures', 'Jours', 'Moy. / semaine', 'Heures sup'];

function cells(p: WorkStats['periods'][number]): string[] {
  const hours = [p.total_hours, p.days_worked, p.week_average];
  return [p.label, hm(hours[0]), String(hours[1]), hm(hours[2])].concat(
    hm(p.overtime_hours),
  );
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
