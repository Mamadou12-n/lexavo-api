import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Animated, {
  useSharedValue, useAnimatedStyle, withSpring,
} from 'react-native-reanimated';
import { colors, typography, elevation, radius, spacing, motion } from '../../theme/designSystem';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

/**
 * ToolCard — carte outil 2 colonnes
 *
 * /impeccable : ZÉRO borderTopWidth (BAN absolu).
 *   Indicateur visuel = petit cercle 4px en haut-gauche (discret, intentionnel).
 * /shape      : fond blanc, iconBox avec teinte légère, radius 16px
 * /stitch-ui-design : cohérent avec Card.js et tous les écrans
 * /premium-frontend-ui : scale spring, indicateur coloré subtil
 */
export const ToolCard = ({
  iconName,
  iconColor,
  title,
  subtitle,
  onPress,
  accessibilityLabel,
}) => {
  const scale = useSharedValue(1);
  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const ic = iconColor || colors.brand;

  return (
    <AnimatedPressable
      onPress={onPress}
      onPressIn={() => {
        scale.value = withSpring(0.97, { damping: 15, stiffness: 400 });
      }}
      onPressOut={() => {
        scale.value = withSpring(1.0, { damping: 15, stiffness: 300 });
      }}
      accessible={true}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel || title}
      style={[styles.card, elevation.low, animatedStyle]}
    >
      {/* Indicateur coloré — cercle 4px. PAS de stripe latérale. */}
      <View style={[styles.dot, { backgroundColor: ic }]} />

      {/* Icône dans un carré teinté */}
      <View style={[styles.iconBox, { backgroundColor: `${ic}18` }]}>
        <Ionicons
          name={iconName || 'document-text-outline'}
          size={22}
          color={ic}
          accessibilityElementsHidden={true}
        />
      </View>

      <Text style={styles.title} numberOfLines={2}>{title}</Text>
      {subtitle ? (
        <Text style={styles.subtitle} numberOfLines={1}>{subtitle}</Text>
      ) : null}
    </AnimatedPressable>
  );
};

const styles = StyleSheet.create({
  card: {
    width: '47%',
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.base,
    position: 'relative',
    overflow: 'hidden',
    // ZÉRO borderTopWidth. ZÉRO borderLeftWidth. JAMAIS.
  },
  dot: {
    position: 'absolute',
    top: 10,
    left: 10,
    width: 4,
    height: 4,
    borderRadius: 2,
  },
  iconBox: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
    marginTop: spacing.sm,
  },
  title: {
    fontFamily: typography.fontBodySemiBold,
    fontSize: typography.sizeSmall,
    color: colors.textPrimary,
    lineHeight: typography.lineSmall,
    marginBottom: 2,
  },
  subtitle: {
    fontFamily: typography.fontBody,
    fontSize: typography.sizeCaption,
    color: colors.textMuted,
    lineHeight: typography.lineCaption,
  },
});

export default ToolCard;
