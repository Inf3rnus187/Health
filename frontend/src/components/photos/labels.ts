export const ANGLE_LABEL: Record<string, string> = {
  face: 'Face',
  profil: 'Profil',
  dos: 'Dos',
};

export const STATUS_LABEL: Record<string, string> = {
  received: 'Reçue',
  normalized: 'Prête',
  analyzed: 'Analysée',
  low_quality: 'Qualité insuffisante',
  ai_failed: 'IA indisponible',
  error: 'Image illisible',
};

export function angleLabel(angle: string): string {
  return ANGLE_LABEL[angle] ?? angle;
}
