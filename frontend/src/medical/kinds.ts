export const KIND_LABELS: Record<string, string> = {
  ordonnance: 'Ordonnance',
  imagerie: 'Imagerie',
  compte_rendu: 'Compte-rendu',
  biologie: 'Biologie (prise de sang)',
  efr: 'EFR (respiratoire)',
  test_marche: 'Test de marche',
  cda: 'Dossier CDA',
  vaccination: 'Vaccination',
  autre: 'Autre',
};

export const KIND_OPTIONS: [string, string][] = Object.entries(KIND_LABELS);
