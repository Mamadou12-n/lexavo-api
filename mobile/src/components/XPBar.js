import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography } from '../theme/designSystem';

/**
 * @typedef {Object} XPBarProps
 * @property {number} currentXP - XP courant de l'utilisateur dans le niveau actuel.
 * @property {number} [nextLevelXP=500] - XP requis pour atteindre le niveau suivant.
 * @property {number} level - Niveau actuel de l'utilisateur (à afficher).
 */

/**
 * XPBar — Barre de progression d'XP du système de gamification Lexavo Campus.
 *
 * @param {XPBarProps} props
 * @returns {React.ReactElement}
 */
export default function XPBar({ currentXP, nextLevelXP = 500, level }) {
  const progress = Math.min((currentXP / nextLevelXP) * 100, 100);

  return (
    <View style={styles.container}>
      <View style={styles.labelRow}>
        <Text style={styles.levelText}>Lvl {level}</Text>
        <Text style={styles.xpText}>{currentXP}/{nextLevelXP} XP</Text>
      </View>
      <View style={styles.trackBar}>
        <View style={[styles.fillBar, { width: `${progress}%` }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 12,
  },
  labelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  levelText: {
    fontFamily: typography.fontBodyBold,
    color: colors.brand,
    fontWeight: '700',
    fontSize: 14,
  },
  xpText: {
    fontFamily: typography.fontBody,
    color: 'rgba(255,255,255,0.70)',
    fontSize: 12,
  },
  trackBar: {
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.15)',
    overflow: 'hidden',
  },
  fillBar: {
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.brand,
  },
});
