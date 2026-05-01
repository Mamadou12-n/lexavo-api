import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, sourceColor } from '../theme/colors';
import { typography, spacing, radius } from '../theme/designSystem';

/**
 * @typedef {Object} SourceCardProps
 * @property {string} source - Nom de la source juridique.
 * @property {number} count - Nombre de documents indexés pour cette source.
 */

/**
 * SourceCard — Carte d'une source dans le rapport de statistiques.
 * /impeccable : ZÉRO borderLeftWidth — indicateur = dot 8px coloré uniquement.
 *
 * @param {SourceCardProps} props
 * @returns {React.ReactElement}
 */
export default function SourceCard({ source, count }) {
  const bg = sourceColor(source);
  return (
    <View style={styles.card}>
      <View style={[styles.dot, { backgroundColor: bg }]} />
      <Text style={styles.name} numberOfLines={1}>{source}</Text>
      <Text style={[styles.count, { color: bg }]}>{count?.toLocaleString() ?? '—'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radius.sm,
    paddingVertical: spacing.sm + 2,
    paddingHorizontal: spacing.md,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 1,
    shadowRadius: 3,
    elevation: 1,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: spacing.sm + 2,
  },
  name: {
    flex: 1,
    fontFamily: typography.fontBodyMedium,
    fontSize: typography.sizeSmall,
    color: colors.textPrimary,
    fontWeight: '500',
  },
  count: {
    fontFamily: typography.fontBodyBold,
    fontSize: typography.sizeBody,
    fontWeight: '700',
  },
});
