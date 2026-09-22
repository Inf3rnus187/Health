// Standardised shooting protocol: day-to-day comparability depends on
// identical conditions far more than on the camera or the AI model.
interface Section {
  title: string;
  items: string[];
}

const SECTIONS: Section[] = [
  {
    title: 'Quand',
    items: [
      'Le matin, à jeun, après être allé aux toilettes.',
      'Avant de boire ou de manger.',
    ],
  },
  {
    title: 'Cadre',
    items: [
      'Même lieu, même éclairage, fond uni.',
      'Même tenue (sous-vêtement).',
      'Téléphone fixe (trépied + retardateur) à hauteur du nombril, ' +
        'à ~2 m.',
      'Cadrage du cou aux genoux.',
    ],
  },
  {
    title: 'Posture',
    items: [
      'Ventre relâché (ni rentré ni gonflé), en fin d’expiration normale.',
      'Face : bras légèrement écartés du corps.',
      'Profil : toujours le même côté, bras croisés sur la poitrine ' +
        'pour dégager le ventre.',
      'Dos : bras légèrement écartés.',
    ],
  },
  {
    title: 'Tour de taille au mètre ruban (1× par semaine)',
    items: [
      'Toujours le même jour, à jeun.',
      'À mi-distance entre la dernière côte et le haut de la hanche ' +
        '(crête iliaque).',
      'En fin d’expiration, ruban horizontal non serré (méthode OMS).',
    ],
  },
];

function ProtocolSection({ section }: { section: Section }) {
  return (
    <div className="protocol-section">
      <h3>{section.title}</h3>
      <ul>
        {section.items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function ProtocolCard() {
  return (
    <details className="card protocol">
      <summary>Protocole de prise de vue (à respecter chaque jour)</summary>
      <div className="protocol-grid">
        {SECTIONS.map((section) => (
          <ProtocolSection key={section.title} section={section} />
        ))}
      </div>
      <p className="protocol-why">
        <strong>Pourquoi :</strong> les variations d’un jour à l’autre (eau,
        repas, ballonnements) sont du bruit ; seule la tendance sur plusieurs
        semaines est interprétable.
      </p>
    </details>
  );
}
