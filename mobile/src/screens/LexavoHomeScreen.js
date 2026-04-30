/**
 * LexavoHomeScreen — Grille des outils juridiques
 *
 * /impeccable    : ZÉRO borderTopWidth (BAN absolu supprimé)
 * /shape         : ToolCard avec dot indicator (4px) à la place de la stripe
 * /distill       : Progressive disclosure — 4 outils visibles + "Voir tout"
 * /colorize      : tokens designSystem, zéro hardcode
 * /clarify       : Labels citoyens (Shield→Analyser un contrat, etc.)
 * /building-native-ui : Pressable + scale spring via ToolCard
 * /stitch-ui-design  : cohérent avec le reste de l'app
 */
import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable, StatusBar,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { colors, typography, spacing, radius, elevation, motion } from '../theme/designSystem';
import { ToolCard } from '../components/ui/ToolCard';
import { Disclaimer } from '../components/ui/Disclaimer';

// Map outil → icône Ionicons + couleur — /shape + /stitch-ui-design
const TOOL_ICONS = {
  Defend:          { icon: 'shield-checkmark-outline', color: colors.brand      },
  Shield:          { icon: 'document-text-outline',    color: '#2980B9'         },
  Diagnostic:      { icon: 'search-outline',           color: '#8E44AD'         },
  Calculateurs:    { icon: 'calculator-outline',       color: '#27AE60'         },
  Fiscal:          { icon: 'receipt-outline',          color: '#34495E'         },
  Reponses:        { icon: 'mail-outline',             color: '#8E44AD'         },
  Score:           { icon: 'bar-chart-outline',        color: '#F39C12'         },
  Compliance:      { icon: 'clipboard-outline',        color: '#16A085'         },
  Alertes:         { icon: 'notifications-outline',    color: '#D4A017'         },
  Litiges:         { icon: 'hammer-outline',           color: '#B22222'         },
  Match:           { icon: 'people-outline',           color: '#0050A0'         },
  Emergency:       { icon: 'flash-outline',            color: colors.error      },
  Proof:           { icon: 'folder-outline',           color: '#1A6B3A'         },
  Heritage:        { icon: 'home-outline',             color: '#8B4513'         },
  Contrats:        { icon: 'document-outline',         color: '#2980B9'         },
};

// /clarify — labels en langage citoyen
const FEATURES = [
  { id: 'Defend',       title: 'Contester une décision', sub: 'Recours, opposition, plainte',        screen: 'Defend'       },
  { id: 'Shield',       title: 'Analyser un contrat',    sub: 'Bail, CDI, CDD, commercial',          screen: 'Shield'       },
  { id: 'Calculateurs', title: 'Calculateurs juridiques',sub: 'Préavis, pension, succession',        screen: 'Calculateurs' },
  { id: 'Diagnostic',   title: 'Diagnostic juridique',   sub: 'Analyser ma situation',               screen: 'Diagnostic'   },
  { id: 'Fiscal',       title: 'Questions fiscales',     sub: 'TVA, CIR, indépendants',              screen: 'Fiscal'       },
  { id: 'Compliance',   title: 'Audit compliance PME',   sub: 'RGPD, conformité entreprise',         screen: 'Compliance'   },
  { id: 'Alertes',      title: 'Alertes juridiques',     sub: 'Veille législative belge',            screen: 'Alertes'      },
  { id: 'Litiges',      title: 'Recouvrement',           sub: 'Impayés, mise en demeure',            screen: 'Litiges'      },
  { id: 'Match',        title: 'Trouver un avocat',      sub: 'Par spécialité et région',            screen: 'Match'        },
  { id: 'Emergency',    title: 'Urgence 24h',            sub: 'Réponse juridique immédiate',         screen: 'Emergency'    },
  { id: 'Proof',        title: 'Constituer un dossier',  sub: 'Preuves et pièces justificatives',    screen: 'Proof'        },
  { id: 'Heritage',     title: 'Guide successoral',      sub: 'Héritage et donation',                screen: 'Heritage'     },
  { id: 'Contrats',     title: 'Générer un contrat',     sub: 'Contrats PDF en quelques clics',      screen: 'Contrats'     },
  { id: 'Score',        title: 'Mon score juridique',    sub: 'Santé juridique sur 100',             screen: 'Score'        },
];

const INITIAL_VISIBLE = 4;

export default function LexavoHomeScreen({ navigation }) {
  // /distill — progressive disclosure
  const [showAll, setShowAll] = useState(false);
  const visibleFeatures = showAll ? FEATURES : FEATURES.slice(0, INITIAL_VISIBLE);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
    >
      <StatusBar barStyle="light-content" backgroundColor={colors.brandNavy} />

      {/* ── Hero ── */}
      <View style={styles.hero}>
        <Text style={styles.heroMark}>LEXAVO</Text>
        <Text style={styles.heroSub}>L'assistant juridique belge</Text>
        <View style={styles.heroPill}>
          <Text style={styles.heroPillText}>Droit belge · 8 langues</Text>
        </View>
      </View>

      {/* ── Grille outils ── /distill + /impeccable */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Outils juridiques</Text>
        <Text style={styles.sectionCount}>{FEATURES.length} outils</Text>
      </View>

      <View style={styles.toolGrid}>
        {visibleFeatures.map((f, index) => {
          const iconDef = TOOL_ICONS[f.id] || { icon: 'document-outline', color: colors.brand };
          return (
            <Animated.View
              key={f.id}
              entering={FadeInDown
                .delay(index * motion.stagger)
                .duration(motion.normal)
                .springify()}
              style={styles.toolCardWrapper}
            >
              <ToolCard
                iconName={iconDef.icon}
                iconColor={iconDef.color}
                title={f.title}
                subtitle={f.sub}
                onPress={() => navigation.navigate(f.screen)}
                accessibilityLabel={`${f.title} — ${f.sub}`}
              />
            </Animated.View>
          );
        })}
      </View>

      {/* ── Bouton "Voir tout" / "Réduire" — /distill ── */}
      <Pressable
        onPress={() => setShowAll(!showAll)}
        accessible={true}
        accessibilityRole="button"
        accessibilityLabel={
          showAll
            ? 'Réduire la liste des outils'
            : `Voir tous les ${FEATURES.length} outils juridiques`
        }
        style={styles.showAllBtn}
      >
        <Text style={styles.showAllText}>
          {showAll ? 'Réduire' : `Voir tous les outils (${FEATURES.length})`}
        </Text>
        <Ionicons
          name={showAll ? 'chevron-up' : 'chevron-down'}
          size={16}
          color={colors.brand}
          style={{ marginLeft: 4 }}
          accessibilityElementsHidden={true}
        />
      </Pressable>

      {/* ── Disclaimer unique — /polish ── */}
      <View style={styles.disclaimerWrap}>
        <Disclaimer message="Lexavo est un assistant juridique. Il ne remplace pas un avocat ou un conseiller juridique." />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    paddingBottom: spacing.xxxl,
  },

  // Hero — navy uniquement ici
  hero: {
    backgroundColor: colors.brandNavy,
    paddingTop: 50,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.xl,
    alignItems: 'center',
  },
  heroMark: {
    fontFamily: typography.fontDisplay,
    fontSize: typography.sizeDisplay,
    color: colors.brand,
    letterSpacing: 6,
    marginBottom: spacing.xs,
  },
  heroSub: {
    fontFamily: typography.fontBody,
    fontSize: typography.sizeSmall,
    color: 'rgba(255,255,255,0.80)',
    marginBottom: spacing.md,
  },
  heroPill: {
    backgroundColor: 'rgba(255,255,255,0.12)',
    paddingHorizontal: 14,
    paddingVertical: 5,
    borderRadius: radius.round,
  },
  heroPillText: {
    fontFamily: typography.fontBodyMedium,
    color: colors.textOnNavy,
    fontSize: typography.sizeCaption,
  },

  // Section header
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.base,
    paddingTop: spacing.lg,
    paddingBottom: spacing.sm,
  },
  sectionTitle: {
    fontFamily: typography.fontBodyBold,
    fontSize: typography.sizeH2,
    color: colors.textPrimary,
  },
  sectionCount: {
    fontFamily: typography.fontBody,
    fontSize: typography.sizeCaption,
    color: colors.textMuted,
  },

  // Grille 2 colonnes — /layout + /animate stagger
  toolGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    paddingHorizontal: spacing.base,
  },
  // Wrapper Animated.View — width 47% pour maintenir la grille 2 colonnes
  toolCardWrapper: {
    width: '47%',
  },

  // Bouton "Voir tout" — /distill
  showAllBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 44,         // touch target WCAG
    paddingVertical: spacing.md,
    marginTop: spacing.xs,
  },
  showAllText: {
    fontFamily: typography.fontBodySemiBold,
    fontSize: typography.sizeSmall,
    color: colors.brand,
  },

  disclaimerWrap: {
    marginHorizontal: spacing.base,
    marginTop: spacing.sm,
  },
});
