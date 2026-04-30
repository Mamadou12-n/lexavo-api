import React from 'react';
import { Text, StyleSheet, Pressable, ActivityIndicator } from 'react-native';
import Animated, {
  useSharedValue, useAnimatedStyle, withSpring,
} from 'react-native-reanimated';
import { colors, typography, spacing, radius } from '../../theme/designSystem';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

/**
 * Button Lexavo — 4 variantes, 3 tailles
 *
 * /adapt           : minHeight 44px (WCAG 2.5.8)
 * /frontend-design : variantes primary/secondary/ghost/danger
 * /premium-frontend-ui : scale spring, disabled state opaque
 * /bolder          : primary = terracotta brand (pas navy, pas gris)
 *
 * RÈGLE : 1 seul bouton primary par écran
 */
export const Button = ({
  label,
  onPress,
  variant = 'primary',   // 'primary' | 'secondary' | 'ghost' | 'danger'
  loading = false,
  disabled = false,
  size = 'md',           // 'sm' | 'md' | 'lg'
  accessibilityLabel,
  style,
}) => {
  const scale = useSharedValue(1);
  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const isDisabled = disabled || loading;

  const variants = {
    primary:   { bg: colors.brand,      text: colors.textOnBrand, border: colors.brand      },
    secondary: { bg: colors.surfaceAlt, text: colors.textPrimary,  border: colors.border     },
    ghost:     { bg: 'transparent',     text: colors.brand,        border: 'transparent'     },
    danger:    { bg: colors.error,      text: '#FFFFFF',           border: colors.error      },
  };

  const sizes = {
    sm: { pv: 8,  ph: 16, fs: typography.sizeSmall },
    md: { pv: 14, ph: 20, fs: typography.sizeBody  },
    lg: { pv: 18, ph: 24, fs: typography.sizeH2    },
  };

  const V = variants[variant] || variants.primary;
  const S = sizes[size] || sizes.md;

  return (
    <AnimatedPressable
      onPress={isDisabled ? null : onPress}
      onPressIn={() => {
        if (!isDisabled) scale.value = withSpring(0.97, { damping: 15, stiffness: 400 });
      }}
      onPressOut={() => {
        scale.value = withSpring(1.0, { damping: 15, stiffness: 300 });
      }}
      accessible={true}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel || label}
      accessibilityState={{ disabled: isDisabled }}
      style={[
        styles.btn,
        {
          backgroundColor:  V.bg,
          borderColor:      V.border,
          paddingVertical:  S.pv,
          paddingHorizontal:S.ph,
          opacity:          isDisabled ? 0.5 : 1,
        },
        animatedStyle,
        style,
      ]}
    >
      {loading
        ? <ActivityIndicator size="small" color={V.text} />
        : <Text style={[styles.label, { color: V.text, fontSize: S.fs }]}>{label}</Text>
      }
    </AnimatedPressable>
  );
};

const styles = StyleSheet.create({
  btn: {
    minHeight: 44,   // WCAG 2.5.8
    borderRadius: radius.md,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontFamily: typography.fontBodySemiBold,
    letterSpacing: 0.2,
  },
});

export default Button;
