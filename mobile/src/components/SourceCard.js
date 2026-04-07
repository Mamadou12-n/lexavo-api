import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { sourceColor } from '../theme/colors';

/**
 * Carte d'une source dans le rapport de statistiques.
 */
export default function SourceCard({ source, count }) {
  const bg = sourceColor(source);
  return (
    <View style={[styles.card, { borderLeftColor: bg }]}>
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
    backgroundColor: '#FFF',
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
    marginBottom: 6,
    borderLeftWidth: 4,
    shadowColor: 'rgba(0,0,0,0.05)',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 1,
    elevation: 1,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 10,
  },
  name: {
    flex: 1,
    fontSize: 13,
    color: '#1A1A2E',
    fontWeight: '500',
  },
  count: {
    fontSize: 14,
    fontWeight: '700',
  },
});
