import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography, spacing, radius } from '../../theme/designSystem';
import { useLanguage } from '../../context/LanguageContext';

/**
 * Disclaimer légal — composant unique
 *
 * /polish : remplace le copy-paste double dans AskScreen (P0 — duplicata)
 * Une seule instance dans l'app, jamais dupliquée.
 * /harden : accessibilityRole="text" pour lecteurs d'écran
 *
 * 2026-05-05 : i18n 4 langues (FR/NL/EN/DE) via useLanguage().
 * Le prop `message` est conserve pour overrides explicites (legacy).
 */
export const Disclaimer = ({ message }) => {
  const { t } = useLanguage();
  const text = message || t('disclaimer');
  return (
    <View
      style={styles.container}
      accessible={true}
      accessibilityRole="text"
      accessibilityLabel={text}
    >
      <Ionicons
        name="information-circle-outline"
        size={14}
        color={colors.warning}
        style={styles.icon}
        accessibilityElementsHidden={true}
      />
      <Text style={styles.text} allowFontScaling={true}>
        {text}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: colors.warningLight,
    borderRadius: radius.sm,
    padding: spacing.sm,
    gap: spacing.xs,
  },
  icon: {
    marginTop: 1,
  },
  text: {
    flex: 1,
    fontFamily: typography.fontBody,
    fontSize: typography.sizeCaption,
    color: '#92400E',
    lineHeight: typography.lineCaption,
  },
});

export default Disclaimer;
