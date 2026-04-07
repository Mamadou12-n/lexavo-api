/**
 * Palette de couleurs — App Droit Belgique
 * Inspirée des couleurs nationales belges (noir, jaune, rouge) + tons juridiques sobres
 */
export const colors = {
  // Primaires
  primary:      '#1A3A5C',   // Bleu marine juridique
  primaryLight: '#2E5F8A',
  primaryDark:  '#0D1F33',

  // Accent belge
  accent:       '#F5A623',   // Jaune belge
  accentDark:   '#C97D0A',

  // Fond
  background:   '#F5F6FA',
  surface:      '#FFFFFF',
  surfaceAlt:   '#EEF1F8',

  // Texte
  textPrimary:  '#1A1A2E',
  textSecondary:'#5A6275',
  textMuted:    '#9CA3AF',
  textOnDark:   '#FFFFFF',

  // Sources (badges)
  sourceHUDOC:       '#7B2FBE',  // Violet CEDH
  sourceEURLEX:      '#0050A0',  // Bleu EU
  sourceJURIDAT:     '#B22222',  // Rouge Cassation
  sourceMONITEUR:    '#1A6B3A',  // Vert Moniteur
  sourceCONSCONST:   '#8B4513',  // Marron Cour const.
  sourceCONSEILETAT: '#2F4F4F',  // Gris ardoise
  sourceCCE:         '#4682B4',  // Bleu acier
  sourceCNT:         '#DC6B19',  // Orange social
  sourceJUSTEL:      '#1A6B3A',  // Vert législation
  sourceAPD:         '#C0392B',  // Rouge RGPD
  sourceGALLILEX:    '#2980B9',  // Bleu FWB
  sourceFSMA:        '#16A085',  // Vert mer finance
  sourceWALLEX:      '#8E44AD',  // Violet Wallonie
  sourceCCREK:       '#D35400',  // Orange audit
  sourceCHAMBRE:     '#27AE60',  // Vert parlement
  sourceCODEXVL:     '#E67E22',  // Orange flamand
  sourceBRUXELLES:   '#3498DB',  // Bleu Bruxelles
  sourceSPFFIN:      '#2C3E50',  // Bleu foncé SPF Finances

  // États
  success:  '#27AE60',
  warning:  '#F39C12',
  error:    '#E74C3C',
  info:     '#2980B9',

  // Bordures
  border:       '#E2E8F0',
  borderDark:   '#CBD5E0',

  // Ombres
  shadow:       'rgba(0,0,0,0.08)',
};

/**
 * Retourne la couleur de badge d'une source juridique.
 */
export function sourceColor(source = '') {
  const s = source.toUpperCase();
  if (s.includes('HUDOC') || s.includes('CEDH'))      return colors.sourceHUDOC;
  if (s.includes('EUR-LEX') || s.includes('CJUE'))    return colors.sourceEURLEX;
  if (s.includes('JURIDAT') || s.includes('CASSATION')) return colors.sourceJURIDAT;
  if (s.includes('MONITEUR'))                          return colors.sourceMONITEUR;
  if (s.includes('CONSTITUTIONNELLE'))                 return colors.sourceCONSCONST;
  if (s.includes("CONSEIL D'ÉTAT"))                    return colors.sourceCONSEILETAT;
  if (s.includes('CCE') || s.includes('ÉTRANGERS'))   return colors.sourceCCE;
  if (s.includes('CNT') || s.includes('TRAVAIL'))     return colors.sourceCNT;
  if (s.includes('JUSTEL'))                            return colors.sourceJUSTEL;
  if (s.includes('APD') || s.includes('RGPD'))        return colors.sourceAPD;
  if (s.includes('GALLILEX') || s.includes('FWB'))    return colors.sourceGALLILEX;
  if (s.includes('FSMA'))                              return colors.sourceFSMA;
  if (s.includes('WALLEX') || s.includes('WALLON'))   return colors.sourceWALLEX;
  if (s.includes('COMPTES') || s.includes('CCREK'))   return colors.sourceCCREK;
  if (s.includes('CHAMBRE'))                           return colors.sourceCHAMBRE;
  if (s.includes('CODEX') || s.includes('VLAANDEREN')) return colors.sourceCODEXVL;
  if (s.includes('BRUXELLES') || s.includes('BXL'))    return colors.sourceBRUXELLES;
  if (s.includes('SPF') || s.includes('FINANCES'))     return colors.sourceSPFFIN;
  return colors.primary;
}
