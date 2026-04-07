import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Linking } from 'react-native';
import { colors } from '../theme/colors';
import SourceBadge from './SourceBadge';

/**
 * Carte d'un résultat de recherche vectorielle.
 * Affiche : source, titre, date, extrait du texte, similarité, lien URL.
 */
export default function ResultCard({ item, onPress }) {
  const similarity = item.similarity != null
    ? `${(item.similarity * 100).toFixed(0)}%`
    : null;

  const handleUrl = () => {
    if (item.url) Linking.openURL(item.url).catch(() => {});
  };

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={onPress}
      activeOpacity={0.85}
    >
      {/* Header : source + date + similarité */}
      <View style={styles.header}>
        <SourceBadge source={item.source || ''} small />
        <View style={styles.headerRight}>
          {item.date ? (
            <Text style={styles.date}>{item.date.slice(0, 10)}</Text>
          ) : null}
          {similarity ? (
            <View style={styles.simBadge}>
              <Text style={styles.simText}>{similarity}</Text>
            </View>
          ) : null}
        </View>
      </View>

      {/* Titre */}
      {item.title ? (
        <Text style={styles.title} numberOfLines={2}>{item.title}</Text>
      ) : null}

      {/* ECLI */}
      {item.ecli ? (
        <Text style={styles.ecli}>{item.ecli}</Text>
      ) : null}

      {/* Extrait du chunk */}
      {item.chunk_text ? (
        <Text style={styles.excerpt} numberOfLines={4}>
          {item.chunk_text.trim()}
        </Text>
      ) : null}

      {/* Footer : URL */}
      {item.url ? (
        <TouchableOpacity activeOpacity={0.75} onPress={handleUrl} style={styles.urlRow}>
          <Text style={styles.urlText} numberOfLines={1}>{item.url}</Text>
        </TouchableOpacity>
      ) : null}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 1,
    shadowRadius: 6,
    elevation: 3,
    borderLeftWidth: 3,
    borderLeftColor: colors.primary,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  date: {
    fontSize: 11,
    color: colors.textMuted,
  },
  simBadge: {
    backgroundColor: colors.primaryLight,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
  },
  simText: {
    color: '#FFF',
    fontSize: 10,
    fontWeight: '700',
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: 4,
    lineHeight: 20,
  },
  ecli: {
    fontSize: 10,
    color: colors.textMuted,
    fontFamily: 'monospace',
    marginBottom: 6,
  },
  excerpt: {
    fontSize: 12,
    color: colors.textSecondary,
    lineHeight: 18,
    marginTop: 4,
  },
  urlRow: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  urlText: {
    fontSize: 10,
    color: colors.primaryLight,
    textDecorationLine: 'underline',
  },
});
