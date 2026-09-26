// French names of the data sources stored with each value.
export const SOURCE_LABEL: Record<string, string> = {
  apple: 'Apple Santé (export)',
  'auto-export': 'Health Auto Export',
  healthkit: 'App iPhone (HealthKit)',
  watch: 'Apple / raccourci (jour)',
  manual: 'Saisie',
  biology: 'Prise de sang (PDF)',
  document: 'Document (lecture exacte)',
  'document-ai': 'Document (IA vérifiée)',
  ai: 'IA photo',
  ppc: 'PPC',
  cda: 'Dossier CDA',
};

export function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source;
}
