import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';

export default function BadgeGrid({ badges, earnedIds }) {
  const earnedSet = new Set(earnedIds);

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.scrollContent}
    >
      {badges.map((badge) => {
        const isEarned = earnedSet.has(badge.id);
        return (
          <View
            key={badge.id}
            style={[
              styles.badgeItem,
              isEarned ? styles.earned : styles.locked,
            ]}
          >
            <Text style={styles.emoji}>{badge.emoji}</Text>
            <Text style={styles.name} numberOfLines={1}>
              {badge.name}
            </Text>
          </View>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    gap: 8,
    paddingHorizontal: 2,
  },
  badgeItem: {
    width: 60,
    height: 70,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0F1629',
    borderRadius: 10,
    padding: 6,
  },
  earned: {
    opacity: 1,
    borderColor: '#00D4AA',
    borderWidth: 1,
  },
  locked: {
    opacity: 0.3,
  },
  emoji: {
    fontSize: 28,
  },
  name: {
    fontSize: 9,
    color: '#F0F4FF',
    marginTop: 4,
    textAlign: 'center',
  },
});
