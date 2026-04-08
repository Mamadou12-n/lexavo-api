import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function StreakCounter({ count, isActive = false }) {
  const showGlow = isActive && count > 0;

  if (count === 0) {
    return (
      <View style={styles.container}>
        <Text style={styles.inactiveText}>Pas de streak</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, showGlow && styles.glow]}>
      <Text style={styles.emoji}>🔥</Text>
      <Text style={[styles.text, showGlow ? styles.activeText : styles.inactiveText]}>
        {count} jours
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0F1629',
    borderRadius: 12,
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  glow: {
    borderColor: '#00D4AA',
    borderWidth: 1,
    shadowColor: '#00D4AA',
    shadowOpacity: 0.5,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 0 },
    elevation: 6,
  },
  emoji: {
    fontSize: 18,
    marginRight: 6,
  },
  text: {
    fontWeight: 'bold',
    fontSize: 14,
  },
  activeText: {
    color: '#F0F4FF',
  },
  inactiveText: {
    color: '#5A6B8A',
  },
});
