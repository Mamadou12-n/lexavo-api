import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { sourceColor } from '../theme/colors';

/**
 * Badge coloré affichant le nom de la source juridique.
 */
export default function SourceBadge({ source, small = false }) {
  const bg = sourceColor(source);
  return (
    <View style={[styles.badge, { backgroundColor: bg }, small && styles.small]}>
      <Text style={[styles.text, small && styles.smallText]} numberOfLines={1}>
        {source}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
    alignSelf: 'flex-start',
    maxWidth: 200,
  },
  small: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
  },
  text: {
    color: '#FFF',
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.2,
  },
  smallText: {
    fontSize: 10,
  },
});
