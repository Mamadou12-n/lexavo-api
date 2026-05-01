import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography, spacing, radius } from '../../theme/designSystem';

/**
 * Disclaimer légal — composant unique
 *
 * /polish : remplace le copy-paste double dans AskScreen (P0 — duplicata)
 * Une seule instance dans l'app, jamais dupliquée.
 * /harden : accessibilityRole="text" pour lecteurs d'écran
 */
export const Disclaimer = ({ message }) => (
  <View
    style={styles.container}
    accessible={true}
    accessibilityRole="text"
    accessibilityLabel={message || "Cette réponse ne constitue pas un avis juridique. Consultez un avocat pour votre situation spécifique."}
  >
    <Ionicons
      name="information-circle-outline"
      size={14}
      color={colors.warning}
      style={styles.icon}
      accessibilityElementsHidden={true}
    />
    <Text style={styles.text} allowFontScaling={true}>
      {message ||
        "Cette réponse ne constitue pas un avis juridique. Consultez un avocat pour votre situation spécifique."}
    </Text>
  </View>
);

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
