import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

export default function XPBar({ currentXP, nextLevelXP = 500, level }) {
  const progress = Math.min((currentXP / nextLevelXP) * 100, 100);

  return (
    <View style={styles.container}>
      <View style={styles.labelRow}>
        <Text style={styles.levelText}>Lvl {level}</Text>
        <Text style={styles.xpText}>{currentXP}/{nextLevelXP} XP</Text>
      </View>
      <View style={styles.trackBar}>
        <LinearGradient
          colors={['#00D4AA', '#8B5CF6']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={[styles.fillBar, { width: `${progress}%` }]}
        />
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
    color: '#00D4AA',
    fontWeight: 'bold',
    fontSize: 14,
  },
  xpText: {
    color: '#5A6B8A',
    fontSize: 12,
  },
  trackBar: {
    height: 10,
    borderRadius: 5,
    backgroundColor: '#1E2A45',
    overflow: 'hidden',
  },
  fillBar: {
    height: 10,
    borderRadius: 5,
  },
});
