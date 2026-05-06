/**
 * QuotaBanner — Bandeau awareness paywall progressif.
 *
 * Affiche selon warning_level :
 * - 'none'     : null (pas de bandeau)
 * - 'soft'     : info bleue "X questions restantes ce mois"
 * - 'hard'     : warning orange "Plus que X questions — passez Basic"
 * - 'blocked'  : danger rouge "Quota atteint — reset le DD/MM"
 *
 * Tap → navigate Subscription
 */
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../theme/designSystem';
import { useLanguage } from '../../context/LanguageContext';

const LEVEL_STYLES = {
  soft: {
    bg: colors.warningLight || '#FEF3C7',
    border: colors.warning || '#F39C12',
    icon: 'information-circle',
    iconColor: '#0369A1',
    textColor: colors.brandNavy || '#1C2B3A',
  },
  hard: {
    bg: '#FFE7DD',
    border: colors.brand || '#C45A2D',
    icon: 'alert-circle',
    iconColor: colors.brandDark || '#9E4522',
    textColor: colors.brandDark || '#9E4522',
  },
  blocked: {
    bg: '#FEE2E2',
    border: '#DC2626',
    icon: 'lock-closed',
    iconColor: '#B91C1C',
    textColor: '#B91C1C',
  },
};

function formatResetDate(iso, lang) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(lang || 'fr-BE', { day: 'numeric', month: 'long' });
  } catch {
    return '';
  }
}

export default function QuotaBanner({ status, onPress }) {
  const { t, lang } = useLanguage();
  if (!status) return null;
  const level = status.warning_level;
  if (!level || level === 'none') return null;

  const cfg = LEVEL_STYLES[level];
  if (!cfg) return null;

  const remaining = status.questions_remaining ?? 0;
  const reset = formatResetDate(status.next_reset, lang);

  let label;
  if (level === 'soft') {
    label = (t('quota_banner_soft') || 'Il vous reste {{n}} questions ce mois.').replace('{{n}}', remaining);
  } else if (level === 'hard') {
    label = (t('quota_banner_hard') || 'Plus que {{n}} questions — passez à Basic.').replace('{{n}}', remaining);
  } else {
    label = (t('quota_banner_blocked') || 'Quota atteint. Reset le {{date}}.').replace('{{date}}', reset);
  }

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.85}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={[styles.container, { backgroundColor: cfg.bg, borderColor: cfg.border }]}
    >
      <Ionicons name={cfg.icon} size={20} color={cfg.iconColor} style={styles.icon} />
      <Text style={[styles.text, { color: cfg.textColor }]} numberOfLines={2}>
        {label}
      </Text>
      <Ionicons name="chevron-forward" size={18} color={cfg.iconColor} />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginHorizontal: 16,
    marginVertical: 8,
    borderRadius: 10,
    borderLeftWidth: 4,
    gap: 10,
  },
  icon: {
    marginRight: 4,
  },
  text: {
    flex: 1,
    fontSize: 13,
    fontFamily: 'Nunito_500Medium',
    lineHeight: 18,
  },
});
