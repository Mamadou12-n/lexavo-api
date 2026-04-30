/**
 * Lexavo — Palette de couleurs
 * Re-export depuis designSystem.js — rétrocompatibilité totale
 * Skills: /colorize
 */
export { colors } from './designSystem';
export { colors as default } from './designSystem';

// Couleurs sources juridiques — conservées intactes
const SOURCE_COLORS = {
  HUDOC:             '#7B2FBE',
  'EUR-LEX':         '#0050A0',
  CJUE:              '#0050A0',
  JURIDAT:           '#B22222',
  CASSATION:         '#B22222',
  MONITEUR:          '#1A6B3A',
  CONSTITUTIONNELLE: '#8B4513',
  "CONSEIL D'ÉTAT":  '#2F4F4F',
  CCE:               '#4682B4',
  ÉTRANGERS:         '#4682B4',
  CNT:               '#DC6B19',
  TRAVAIL:           '#DC6B19',
  JUSTEL:            '#1A6B3A',
  APD:               '#C0392B',
  RGPD:              '#C0392B',
  GALLILEX:          '#2980B9',
  FWB:               '#2980B9',
  FSMA:              '#16A085',
  WALLEX:            '#8E44AD',
  WALLON:            '#8E44AD',
  COMPTES:           '#D35400',
  CCREK:             '#D35400',
  CHAMBRE:           '#27AE60',
  CODEX:             '#E67E22',
  VLAANDEREN:        '#E67E22',
  BRUXELLES:         '#3498DB',
  BXL:               '#3498DB',
  SPF:               '#2C3E50',
  FINANCES:          '#2C3E50',
};

/**
 * Retourne la couleur de badge d'une source juridique.
 */
export function sourceColor(source = '') {
  const s = source.toUpperCase();
  for (const [key, color] of Object.entries(SOURCE_COLORS)) {
    if (s.includes(key)) return color;
  }
  return '#5A6275'; // colors.textSecondary fallback
}
