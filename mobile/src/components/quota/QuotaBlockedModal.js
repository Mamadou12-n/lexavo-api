/**
 * QuotaBlockedModal — Modal bloquante à 100% (warning_level='blocked').
 *
 * Affichée à chaque tentative quand quota épuisé.
 * Pas dismissable sans action — soit upgrade soit fermer (ferme la fenêtre,
 * mais le quota reste bloqué côté backend).
 */
import React from 'react';
import { Modal, View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../theme/designSystem';
import { useLanguage } from '../../context/LanguageContext';

function formatResetDate(iso, lang) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(lang || 'fr-BE', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  } catch {
    return '';
  }
}

export default function QuotaBlockedModal({ visible, status, onUpgrade, onClose }) {
  const { t, lang } = useLanguage();
  if (!status) return null;

  const reset = formatResetDate(status.next_reset, lang);
  const used = status.questions_used ?? 0;
  const limit = status.questions_limit ?? 0;

  const title = t('quota_modal_blocked_title') || 'Quota mensuel atteint';
  const body = (t('quota_modal_blocked_body') ||
    'Vous avez utilisé vos {{used}}/{{limit}} questions ce mois. Reset le {{date}}.'
  ).replace('{{used}}', used).replace('{{limit}}', limit).replace('{{date}}', reset);
  const sub = t('quota_modal_blocked_sub') || 'Passez à un plan payant pour un accès illimité dès maintenant.';
  const ctaUpgrade = t('quota_modal_blocked_cta') || 'Voir les plans';
  const ctaClose = t('quota_modal_blocked_close') || 'Fermer';

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.card}>
          <View style={styles.iconWrap}>
            <Ionicons name="lock-closed" size={36} color="#B91C1C" />
          </View>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.body}>{body}</Text>
          <Text style={styles.sub}>{sub}</Text>

          <TouchableOpacity
            onPress={onUpgrade}
            accessibilityRole="button"
            accessibilityLabel={ctaUpgrade}
            style={styles.ctaPrimary}
          >
            <Text style={styles.ctaPrimaryText}>{ctaUpgrade}</Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={onClose}
            accessibilityRole="button"
            accessibilityLabel={ctaClose}
            style={styles.ctaSecondary}
          >
            <Text style={styles.ctaSecondaryText}>{ctaClose}</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(28, 43, 58, 0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  card: {
    backgroundColor: '#FAF7F2',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 360,
    alignItems: 'center',
  },
  iconWrap: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: '#FEE2E2',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 19,
    fontFamily: 'EBGaramond_600SemiBold',
    color: colors.brandNavy || '#1C2B3A',
    textAlign: 'center',
    marginBottom: 10,
  },
  body: {
    fontSize: 14,
    fontFamily: 'Nunito_500Medium',
    color: colors.brandNavy || '#1C2B3A',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 8,
  },
  sub: {
    fontSize: 13,
    fontFamily: 'Nunito_400Regular',
    color: colors.brandNavy || '#1C2B3A',
    textAlign: 'center',
    opacity: 0.75,
    marginBottom: 20,
  },
  ctaPrimary: {
    backgroundColor: colors.brand || '#C45A2D',
    paddingVertical: 12,
    paddingHorizontal: 32,
    borderRadius: 10,
    width: '100%',
    alignItems: 'center',
    marginBottom: 8,
  },
  ctaPrimaryText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontFamily: 'Nunito_600SemiBold',
  },
  ctaSecondary: {
    paddingVertical: 10,
    paddingHorizontal: 24,
  },
  ctaSecondaryText: {
    color: colors.brandNavy || '#1C2B3A',
    fontSize: 14,
    fontFamily: 'Nunito_500Medium',
    opacity: 0.7,
  },
});
