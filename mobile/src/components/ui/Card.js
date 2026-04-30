import React from 'react';
import { View, StyleSheet, Pressable } from 'react-native';
import Animated, {
  useSharedValue, useAnimatedStyle, withSpring,
} from 'react-native-reanimated';
import { colors, elevation, radius, spacing, motion } from '../../theme/designSystem';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

/**
 * Card universelle Lexavo
 *
 * /impeccable : PAS de borderTopWidth. PAS de borderLeftWidth. PAS de glow.
 * /shape      : fond blanc, ombre teinté navy, radius 16px
 * /building-native-ui : scale spring sur press, accessibilityRole button
 * /premium-frontend-ui : élévation configurable (low/medium/high)
 */
export const Card = ({
  children,
  onPress,
  style,
  elevationLevel = 'low',
  accessibilityLabel,
  accessibilityHint,
}) => {
  const scale = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  if (!onPress) {
    return (
      <View style={[styles.card, elevation[elevationLevel], style]}>
        {children}
      </View>
    );
  }

  return (
    <AnimatedPressable
      onPress={onPress}
      onPressIn={() => {
        scale.value = withSpring(motion.scalePressIn, { damping: 15, stiffness: 400 });
      }}
      onPressOut={() => {
        scale.value = withSpring(motion.scalePressOut, { damping: 15, stiffness: 300 });
      }}
      accessible={true}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      accessibilityHint={accessibilityHint}
      style={[styles.card, elevation[elevationLevel], animatedStyle, style]}
    >
      {children}
    </AnimatedPressable>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.base,
    // ZÉRO borderTopWidth. ZÉRO borderLeftWidth. JAMAIS.
  },
});

export default Card;
