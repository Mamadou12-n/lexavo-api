/**
 * QuotaWarningModal — Modal incitation à 80% (warning_level='hard').
 *
 * Affichée 1x par session (flag AsyncStorage). Dismissable.
 * CTA primaire → Subscription, secondaire → fermer.
 */
import React from 'react';
import { Modal, View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../theme/designSystem';
import { useLanguage } from '../../context/LanguageContext';

export default function QuotaWarningModal({ visible, status, onUpgrade, onDismiss }) {
  const { t } = useLanguage();
  if (!status) return null;
  const remaining = status.questions_remaining ?? 0;

  const title = t('quota_modal_warn_title') || 'Bientôt à court de questions';
  const body = (t('quota_modal_warn_body') ||
    'Plus que {{n}} questions ce mois-ci. Passez à Basic (4,99€/mois) pour un accès illimité.'
  ).replace('{{n}}', remaining);
  const ctaUpgrade = t('quota_modal_warn_cta') || 'Voir les plans';
  const ctaDismiss = t('quota_modal_warn_dismiss') || 'Plus tard';

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onDismiss}
    >
      <View style={styles.overlay}>
        <View style={styles.card}>
          <View style={styles.iconWrap}>
            <Ionicons name="warning" size={32} color={colors.brand || '#C45A2D'} />
          </View>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.body}>{body}</Text>

          <TouchableOpacity
            onPress={onUpgrade}
            accessibilityRole="button"
            accessibilityLabel={ctaUpgrade}
            style={styles.ctaPrimary}
          >
            <Text style={styles.ctaPrimaryText}>{ctaUpgrade}</Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={onDismiss}
            accessibilityRole="button"
            accessibilityLabel={ctaDismiss}
            style={styles.ctaSecondary}
          >
            <Text style={styles.ctaSecondaryText}>{ctaDismiss}</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(28, 43, 58, 0.65)',
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
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#FEF3C7',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 18,
    fontFamily: 'EBGaramond_600SemiBold',
    color: colors.brandNavy || '#1C2B3A',
    textAlign: 'center',
    marginBottom: 8,
  },
  body: {
    fontSize: 14,
    fontFamily: 'Nunito_400Regular',
    color: colors.brandNavy || '#1C2B3A',
    textAlign: 'center',
    lineHeight: 20,
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
