import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, radius, spacing } from '../theme/designSystem';

export default function StreakCounter({ count, isActive = false }) {
  if (count === 0) {
    return (
      <View style={styles.container}>
        <Text style={styles.inactiveText}>Pas de streak</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, isActive && styles.active]}>
      <Text style={styles.emoji}>🔥</Text>
      <Text style={[styles.text, isActive ? styles.activeText : styles.inactiveText]}>
        {count} jours
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.10)',
    borderRadius: radius.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
  },
  active: {
    borderColor: colors.brand,
    backgroundColor: `${colors.brand}20`,
  },
  emoji: {
    fontSize: 18,
    marginRight: 6,
  },
  text: {
    fontFamily: typography.fontBodyBold,
    fontWeight: '700',
    fontSize: 14,
  },
  activeText: {
    color: colors.textOnNavy,
  },
  inactiveText: {
    fontFamily: typography.fontBody,
    color: 'rgba(255,255,255,0.60)',
  },
});
