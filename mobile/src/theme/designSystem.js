// ================================================================
// LEXAVO DESIGN SYSTEM — Source unique de vérité
// Autoritaire. Accessible. Protecteur.
// Skills appliquées: /theme-factory /colorize /typeset /layout
//                   /shape /animate /adapt /web-design-guidelines
// ================================================================

// COULEURS — /colorize
export const colors = {
  // Fonds
  background:    '#F7F5F2',   // Ivoire teinté — papier chaud
  surface:       '#FFFFFF',   // Cartes — contraste propre
  surfaceAlt:    '#F0EDE9',   // Fond alternatif

  // Marque
  brand:         '#C45A2D',   // Terracotta brique — accent unique
  brandLight:    '#E8795A',   // Terracotta clair
  brandDark:     '#9E4522',   // Terracotta sombre
  brandNavy:     '#1C2B3A',   // Navy — UNIQUEMENT hero/headers
  brandNavyLight:'#2E4259',   // Navy clair

  // Texte
  textPrimary:   '#1C2B3A',   // Corps principal
  textSecondary: '#5A6275',   // Corps secondaire
  textMuted:     '#6B7280',   // Captions — WCAG AA OK (ratio 4.69:1 sur surface)
  textOnBrand:   '#FFFFFF',   // Sur fond terracotta
  textOnNavy:    '#FFFFFF',   // Sur fond navy

  // Bordures
  border:        '#E8E4DF',   // Ivoire-gris
  borderStrong:  '#C8C4BF',   // Bordure forte

  // Ombres (teintées navy — /polish)
  shadow:        'rgba(28,43,58,0.08)',
  shadowMedium:  'rgba(28,43,58,0.14)',
  shadowStrong:  'rgba(28,43,58,0.22)',

  // Overlay
  overlay:       'rgba(28,43,58,0.5)',

  // États sémantiques
  success:       '#27AE60',
  successLight:  '#EBF9F2',
  warning:       '#F39C12',
  warningLight:  '#FEF3C7',
  error:         '#E74C3C',
  errorLight:    '#FEF0EF',
  info:          '#2980B9',
  infoLight:     '#EBF4FB',

  // Legacy — conservé pour sourceColor() et rétrocompatibilité
  primary:       '#1A3A5C',
  primaryLight:  '#2E5F8A',
  primaryDark:   '#0D1F33',
  accent:        '#C45A2D',   // alias brand
  textOnDark:    '#FFFFFF',   // alias textOnNavy
};

// TYPOGRAPHIE — /typeset
// EB Garamond : titres display (autoritaire, serré, confiance)
// Nunito : corps (lisible, accessible, chaleureux)
export const typography = {
  // Familles
  fontDisplay:       'EBGaramond_700Bold',
  fontDisplayItalic: 'EBGaramond_700BoldItalic',
  fontBody:          'Nunito_400Regular',
  fontBodyMedium:    'Nunito_500Medium',
  fontBodySemiBold:  'Nunito_600SemiBold',
  fontBodyBold:      'Nunito_700Bold',

  // Tailles — échelle 1.25 (Major Third)
  sizeDisplay: 32,
  sizeH1:      24,
  sizeH2:      20,
  sizeBody:    16,
  sizeSmall:   13,
  sizeCaption: 11,

  // Line-heights — ratio ~1.25
  lineDisplay: 40,
  lineH1:      32,
  lineH2:      28,
  lineBody:    24,
  lineSmall:   20,
  lineCaption: 18,
};

// SPACING 4pt — /layout
export const spacing = {
  xs:    4,
  sm:    8,
  md:    12,
  base:  16,
  lg:    20,
  xl:    24,
  xxl:   32,
  xxxl:  48,
  huge:  64,
};

// BORDER RADIUS — /shape
export const radius = {
  sm:    8,
  md:    12,
  lg:    16,
  xl:    20,
  round: 999,
};

// ÉLÉVATION 3 niveaux — /shape
// Ombres teintées navy (jamais #000 pur)
export const elevation = {
  low: {
    shadowColor:   'rgba(28,43,58,0.08)',
    shadowOffset:  { width: 0, height: 1 },
    shadowOpacity: 1,
    shadowRadius:  3,
    elevation:     2,
  },
  medium: {
    shadowColor:   'rgba(28,43,58,0.12)',
    shadowOffset:  { width: 0, height: 3 },
    shadowOpacity: 1,
    shadowRadius:  8,
    elevation:     4,
  },
  high: {
    shadowColor:   'rgba(28,43,58,0.20)',
    shadowOffset:  { width: 0, height: 8 },
    shadowOpacity: 1,
    shadowRadius:  20,
    elevation:     10,
  },
};

// MOTION — /animate + /design-motion-principles
// Spring physics, exit < enter, stagger 40ms
export const motion = {
  fast:         150,
  normal:       280,    // durée principale
  slow:         400,
  stagger:      40,     // délai entre items de liste
  scalePressIn: 0.97,
  scalePressOut:1.0,
};

// TOUCH — /adapt + /web-design-guidelines (WCAG 2.5.8)
export const touch = {
  minSize:    44,   // minimum requis WCAG
  minSpacing: 8,
};
