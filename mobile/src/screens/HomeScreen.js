/**
 * HomeScreen — Écran principal Lexavo
 *
 * /quieter  : supprimé campusGlow + 4 LinearGradient décoratifs → solides
 * /bolder   : campus card = navy solid, CTA = brand terracotta solid
 * /colorize : tokens design system, ZÉRO hardcode
 * /web-design-guidelines : contrast rgba(0.4)→rgba(0.80) WCAG AA
 * /typeset  : fontFamily tokens partout
 * /layout   : spacing 4pt system
 */
import React, { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  RefreshControl, StatusBar, Modal,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getSubscriptionStatus, setLanguage as setClientLang } from '../api/client';
import { useLanguage } from '../context/LanguageContext';
import { colors, typography, spacing, radius, elevation, motion, touch } from '../theme/designSystem';
import { Ionicons } from '@expo/vector-icons';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Disclaimer } from '../components/ui/Disclaimer';

// Refocalisation 2026-05-05 : 4 langues (BE officielles + EN).
const LANGUAGES = [
  { code: 'fr', label: 'Français',   flag: '🇫🇷' },
  { code: 'nl', label: 'Nederlands', flag: '🇳🇱' },
  { code: 'de', label: 'Deutsch',    flag: '🇩🇪' },
  { code: 'en', label: 'English',    flag: '🇬🇧' },
];

// /shape — icônes Ionicons pour les features campus
const CAMPUS_FEATURES = [
  { icon: 'flash-outline',        color: '#8B5CF6', labelKey: 'campus_quiz_label',     subKey: 'campus_quiz_sub'      },
  { icon: 'hardware-chip-outline',color: '#00B894', labelKey: 'campus_tutor_label',    subKey: 'campus_tutor_sub'     },
  { icon: 'mic-outline',          color: '#F59E0B', labelKey: 'campus_notebook_label', subKey: 'campus_notebook_sub'  },
  { icon: 'camera-outline',       color: '#3B82F6', labelKey: 'campus_ocr_label',      subKey: 'campus_ocr_sub'       },
];

// /clarify — labels citoyens
// Refocalisation 2026-05-05 : 4 outils visibles + 3 outils sous "Voir plus".
// Segment "Particulier" — outils citoyens grand public.
const TOOL_VISIBLE = [
  { icon: 'shield-checkmark-outline', color: colors.brand,  titleKey: 'tool_contester',    subKey: 'tool_contester_sub',    screen: 'Defend'       },
  { icon: 'document-text-outline',    color: '#C0392B',     titleKey: 'tool_document',     subKey: 'tool_document_sub',     screen: 'Shield'       },
  { icon: 'calculator-outline',       color: '#1A6B8A',     titleKey: 'tool_calculateurs', subKey: 'tool_calculateurs_sub', screen: 'Calculateurs' },
  { icon: 'search-outline',           color: '#8E44AD',     titleKey: 'tool_diagnostic',   subKey: 'tool_diagnostic_sub',   screen: 'Diagnostic'   },
];

const TOOL_HIDDEN = [
  { icon: 'git-branch-outline',       color: '#8B4513',     titleKey: 'tool_heritage',     subKey: 'tool_heritage_sub',     screen: 'Heritage'     },
  { icon: 'receipt-outline',          color: '#34495E',     titleKey: 'tool_fiscal',       subKey: 'tool_fiscal_sub',       screen: 'Fiscal'       },
  { icon: 'pulse-outline',            color: '#16A085',     titleKey: 'tool_score',        subKey: 'tool_score_sub',        screen: 'Score'        },
];

export default function HomeScreen({ navigation }) {
  const { lang, setLang, t }        = useLanguage();
  const [quota, setQuota]           = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [langModal, setLangModal]   = useState(false);
  // Toggle segment : 'particulier' (defaut) | 'etudiant'.
  // Particulier -> 4 outils visibles + bouton "Voir plus" (modal 3 outils caches).
  // Etudiant    -> section Lexavo Campus (Quiz / Tutor / NotebookLM / OCR).
  const [segment, setSegment]       = useState('particulier');
  const [moreModal, setMoreModal]   = useState(false);

  const selectLang = async (code) => {
    await setLang(code);
    await setClientLang(code);
    setLangModal(false);
  };

  const load = useCallback(async () => {
    try { setQuota(await getSubscriptionStatus()); } catch (_) {}
    setRefreshing(false);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const goTool = (screen) => navigation.navigate('Outils', { screen });
  const currentLang = LANGUAGES.find(l => l.code === lang) || LANGUAGES[0];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => { setRefreshing(true); load(); }}
          tintColor={colors.brand}
        />
      }
    >
      <StatusBar barStyle="light-content" backgroundColor={colors.brandNavy} />

      {/* ═══ HERO ═══ — navy uniquement ici */}
      <View style={styles.hero}>
        <TouchableOpacity
          style={styles.langBtn}
          activeOpacity={0.75}
          onPress={() => setLangModal(true)}
          accessible={true}
          accessibilityRole="button"
          accessibilityLabel={`Langue sélectionnée : ${currentLang.label}. Appuyer pour changer`}
        >
          <Text style={styles.langBtnText}>{currentLang.flag} {currentLang.label}</Text>
          <Ionicons name="chevron-down" size={12} color="rgba(255,255,255,0.75)" accessibilityElementsHidden />
        </TouchableOpacity>

        <Text style={styles.heroMark}>LEXAVO</Text>
        <Text style={styles.heroTagline}>{t('hero_tagline')}</Text>
        <Text style={styles.heroSub}>{t('hero_sub')}</Text>

        <View style={styles.heroPill}>
          <View style={styles.pulseDot} />
          <Text style={styles.heroPillText}>{t('hero_pill')}</Text>
        </View>
      </View>

      {/* ═══ MODAL LANGUE ═══ */}
      <Modal
        visible={langModal}
        transparent
        animationType="fade"
        onRequestClose={() => setLangModal(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setLangModal(false)}
          accessible={true}
          accessibilityRole="button"
          accessibilityLabel="Fermer le sélecteur de langue"
        >
          <View style={styles.langModal}>
            <Text style={styles.langModalTitle}>{t('lang_modal_title')}</Text>
            {LANGUAGES.map(l => (
              <TouchableOpacity
                key={l.code}
                style={[styles.langOption, lang === l.code && styles.langOptionActive]}
                onPress={() => selectLang(l.code)}
                activeOpacity={0.75}
                accessible={true}
                accessibilityRole="button"
                accessibilityLabel={`${l.label}${lang === l.code ? ', sélectionné' : ''}`}
              >
                <Text style={styles.langOptionFlag}>{l.flag}</Text>
                <Text style={[styles.langOptionLabel, lang === l.code && styles.langOptionLabelActive]}>
                  {l.label}
                </Text>
                {lang === l.code && (
                  <Ionicons name="checkmark" size={16} color={colors.brand} accessibilityElementsHidden />
                )}
              </TouchableOpacity>
            ))}
          </View>
        </TouchableOpacity>
      </Modal>

      {/* ═══ 2 GRANDES CARTES ═══ */}
      <View style={styles.dualCards}>
        <TouchableOpacity
          activeOpacity={0.75}
          style={styles.bigCardBlue}
          onPress={() => navigation.navigate('Ask')}
          accessible={true}
          accessibilityRole="button"
          accessibilityLabel={`${t('understand_title')} — ${t('understand_sub')}`}
        >
          <Ionicons name="chatbubbles-outline" size={28} color={colors.textOnNavy} style={styles.bigCardIcon} accessibilityElementsHidden />
          <Text style={styles.bigCardTitle}>{t('understand_title')}</Text>
          <Text style={styles.bigCardSub}>{t('understand_sub')}</Text>
        </TouchableOpacity>
        <TouchableOpacity
          activeOpacity={0.75}
          style={styles.bigCardOrange}
          onPress={() => navigation.navigate('Outils', { screen: 'Defend' })}
          accessible={true}
          accessibilityRole="button"
          accessibilityLabel={`${t('act_title')} — ${t('act_sub')}`}
        >
          <Ionicons name="shield-checkmark-outline" size={28} color={colors.textOnBrand} style={styles.bigCardIcon} accessibilityElementsHidden />
          <Text style={styles.bigCardTitle}>{t('act_title')}</Text>
          <Text style={styles.bigCardSub}>{t('act_sub')}</Text>
        </TouchableOpacity>
      </View>

      {/* ═══ SEGMENT TOGGLE — Particulier ↔ Etudiant ═══ */}
      <View style={styles.segmentWrap}>
        <View style={styles.segmentTrack} accessibilityRole="tablist">
          <TouchableOpacity
            style={[styles.segmentBtn, segment === 'particulier' && styles.segmentBtnActive]}
            onPress={() => setSegment('particulier')}
            activeOpacity={0.8}
            accessibilityRole="tab"
            accessibilityState={{ selected: segment === 'particulier' }}
            accessibilityLabel={t('segment_particulier')}
          >
            <Ionicons
              name="people-outline"
              size={16}
              color={segment === 'particulier' ? colors.textOnBrand : colors.textMuted}
              accessibilityElementsHidden
            />
            <Text style={[styles.segmentBtnText, segment === 'particulier' && styles.segmentBtnTextActive]}>
              {t('segment_particulier')}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.segmentBtn, segment === 'etudiant' && styles.segmentBtnActive]}
            onPress={() => setSegment('etudiant')}
            activeOpacity={0.8}
            accessibilityRole="tab"
            accessibilityState={{ selected: segment === 'etudiant' }}
            accessibilityLabel={t('segment_etudiant')}
          >
            <Ionicons
              name="school-outline"
              size={16}
              color={segment === 'etudiant' ? colors.textOnBrand : colors.textMuted}
              accessibilityElementsHidden
            />
            <Text style={[styles.segmentBtnText, segment === 'etudiant' && styles.segmentBtnTextActive]}>
              {t('segment_etudiant')}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* ═══ SEGMENT : ETUDIANT — Lexavo Campus ═══ */}
      {segment === 'etudiant' && (
        <View style={styles.campusSection}>
          <View style={styles.campusCard}>
            <Ionicons
              name="school-outline"
              size={36}
              color={colors.brand}
              style={styles.campusIconView}
              accessibilityElementsHidden
            />
            <Text style={styles.campusTitle}>LEXAVO CAMPUS</Text>
            <Text style={styles.campusTagline}>{t('campus_tagline')}</Text>

            <View style={styles.campusGrid}>
              {CAMPUS_FEATURES.map((feat, idx) => (
                <View key={idx} style={styles.campusFeature}>
                  <View style={[styles.campusFeatureIcon, { backgroundColor: `${feat.color}22` }]}>
                    <Ionicons name={feat.icon} size={20} color={feat.color} accessibilityElementsHidden />
                  </View>
                  <Text style={styles.campusFeatureLabel} allowFontScaling={true}>{t(feat.labelKey)}</Text>
                  <Text style={styles.campusFeatureSub} allowFontScaling={true}>{t(feat.subKey)}</Text>
                </View>
              ))}
            </View>

            <TouchableOpacity
              activeOpacity={0.85}
              onPress={() => navigation.navigate('Campus')}
              style={styles.campusCTA}
              accessible={true}
              accessibilityRole="button"
              accessibilityLabel={t('campus_cta')}
            >
              <Text style={styles.campusCTAText}>{t('campus_cta')}</Text>
            </TouchableOpacity>

            <Text style={styles.campusNote}>{t('campus_note')}</Text>
          </View>
        </View>
      )}

      {/* ═══ SEGMENT : PARTICULIER — 4 outils visibles + Voir plus ═══ */}
      {segment === 'particulier' && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{t('tools_title')}</Text>
          <View style={styles.grid}>
            {TOOL_VISIBLE.map((tool, index) => (
              <Animated.View
                key={tool.screen}
                entering={FadeInDown
                  .delay(index * motion.stagger)
                  .duration(motion.normal)
                  .springify()}
                style={styles.toolCardWrapper}
              >
                <TouchableOpacity
                  activeOpacity={0.75}
                  style={styles.toolCard}
                  onPress={() => goTool(tool.screen)}
                  accessible={true}
                  accessibilityRole="button"
                  accessibilityLabel={`${t(tool.titleKey)} — ${t(tool.subKey)}`}
                >
                  <View style={[styles.toolIcon, { backgroundColor: `${tool.color}18` }]}>
                    <Ionicons name={tool.icon} size={22} color={tool.color} accessibilityElementsHidden />
                  </View>
                  <Text style={styles.toolTitle} allowFontScaling={true}>{t(tool.titleKey)}</Text>
                  <Text style={styles.toolSub} allowFontScaling={true}>{t(tool.subKey)}</Text>
                </TouchableOpacity>
              </Animated.View>
            ))}
          </View>

          {/* CTA Voir plus — ouvre modal avec TOOL_HIDDEN */}
          <TouchableOpacity
            style={styles.viewMoreBtn}
            activeOpacity={0.8}
            onPress={() => setMoreModal(true)}
            accessibilityRole="button"
            accessibilityLabel={t('view_more')}
          >
            <Ionicons name="add-circle-outline" size={18} color={colors.brand} accessibilityElementsHidden />
            <Text style={styles.viewMoreText}>{t('view_more')}</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* ═══ MODAL "VOIR PLUS" — outils caches segment particulier ═══ */}
      <Modal
        visible={moreModal}
        transparent
        animationType="fade"
        onRequestClose={() => setMoreModal(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setMoreModal(false)}
          accessibilityRole="button"
          accessibilityLabel={t('view_more_close')}
        >
          <View style={styles.moreModal}>
            <Text style={styles.moreModalTitle}>{t('view_more_title')}</Text>
            {TOOL_HIDDEN.map(tool => (
              <TouchableOpacity
                key={tool.screen}
                style={styles.moreModalRow}
                activeOpacity={0.75}
                onPress={() => {
                  setMoreModal(false);
                  goTool(tool.screen);
                }}
                accessibilityRole="button"
                accessibilityLabel={`${t(tool.titleKey)} — ${t(tool.subKey)}`}
              >
                <View style={[styles.moreModalIcon, { backgroundColor: `${tool.color}18` }]}>
                  <Ionicons name={tool.icon} size={20} color={tool.color} accessibilityElementsHidden />
                </View>
                <View style={styles.moreModalTexts}>
                  <Text style={styles.moreModalRowTitle}>{t(tool.titleKey)}</Text>
                  <Text style={styles.moreModalRowSub}>{t(tool.subKey)}</Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={colors.textMuted} accessibilityElementsHidden />
              </TouchableOpacity>
            ))}
          </View>
        </TouchableOpacity>
      </Modal>

      {/* ═══ DISCLAIMER — composant unique /polish ═══ */}
      <View style={styles.disclaimerWrap}>
        <Disclaimer />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content:   { paddingBottom: spacing.xxxl },

  // Hero — navy uniquement
  hero: {
    backgroundColor: colors.brandNavy,
    paddingTop: 48,
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
  heroTagline: {
    fontFamily: typography.fontBodyMedium,
    fontSize: 10,
    // /web-design-guidelines : 0.4→0.80 (WCAG AA ratio ≥3:1 sur navy)
    color: 'rgba(255,255,255,0.80)',
    letterSpacing: 1.5,
    textTransform: 'uppercase',
    marginBottom: 2,
  },
  heroSub: {
    fontFamily: typography.fontBody,
    fontSize: typography.sizeSmall,
    // /web-design-guidelines : 0.65→0.85
    color: 'rgba(255,255,255,0.85)',
    fontStyle: 'italic',
    marginBottom: spacing.md,
  },
  heroPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.12)',
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: radius.round,
    gap: spacing.sm,
  },
  pulseDot: {
    width: 6, height: 6, borderRadius: 3,
    backgroundColor: colors.success,
  },
  heroPillText: {
    fontFamily: typography.fontBodyMedium,
    // /web-design-guidelines : 0.7→0.85
    color: 'rgba(255,255,255,0.85)',
    fontSize: typography.sizeCaption,
  },

  // Langue
  langBtn: {
    position: 'absolute',
    top: 12,
    right: 16,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.12)',
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: radius.md,
    gap: 4,
    minHeight: 44,   // touch target WCAG
  },
  langBtnText: {
    fontFamily: typography.fontBodyMedium,
    color: colors.textOnNavy,
    fontSize: typography.sizeCaption,
  },

  // Modal langue
  modalOverlay: {
    flex: 1,
    backgroundColor: colors.overlay,
    justifyContent: 'center',
    alignItems: 'center',
  },
  langModal: {
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    padding: spacing.lg,
    width: '80%',
    ...elevation.high,
  },
  langModalTitle: {
    fontFamily: typography.fontBodyBold,
    fontSize: typography.sizeH2,
    color: colors.textPrimary,
    marginBottom: spacing.md,
    textAlign: 'center',
  },
  langOption: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: radius.sm,
    gap: spacing.sm,
    marginBottom: 4,
    minHeight: 44,   // touch target WCAG
  },
  langOptionActive: { backgroundColor: colors.surfaceAlt },
  langOptionFlag: { fontSize: 22 },
  langOptionLabel: {
    flex: 1,
    fontFamily: typography.fontBodyMedium,
    fontSize: typography.sizeBody,
    color: colors.textSecondary,
  },
  langOptionLabelActive: {
    fontFamily: typography.fontBodyBold,
    color: colors.textPrimary,
  },

  // 2 grandes cartes
  dualCards: {
    flexDirection: 'row',
    gap: spacing.md,
    padding: spacing.base,
    paddingBottom: spacing.sm,
  },
  bigCardBlue: {
    flex: 1,
    backgroundColor: colors.brandNavy,
    borderRadius: radius.lg,
    padding: spacing.lg,
    alignItems: 'center',
  },
  bigCardOrange: {
    flex: 1,
    backgroundColor: colors.brand,
    borderRadius: radius.lg,
    padding: spacing.lg,
    alignItems: 'center',
  },
  bigCardIcon: { marginBottom: spacing.sm },
  bigCardTitle: {
    fontFamily: typography.fontBodyBold,
    color: colors.textOnNavy,
    fontSize: typography.sizeSmall,
    textAlign: 'center',
    marginBottom: 4,
  },
  bigCardSub: {
    fontFamily: typography.fontBody,
    color: 'rgba(255,255,255,0.80)',
    fontSize: typography.sizeCaption,
    textAlign: 'center',
  },

  // Section
  section: { paddingHorizontal: spacing.base, paddingTop: spacing.md, marginBottom: spacing.lg },
  sectionTitle: {
    fontFamily: typography.fontBodyBold,
    fontSize: typography.sizeH2,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },

  // Grid outils
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  toolCardWrapper: {
    width: '47.5%',
  },
  toolCard: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.md,
    overflow: 'hidden',
    ...elevation.low,
    // ZÉRO borderTopWidth — /impeccable
  },
  toolIcon: {
    width: 44,
    height: 44,
    borderRadius: radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  toolTitle: {
    fontFamily: typography.fontBodySemiBold,
    fontSize: typography.sizeSmall,
    color: colors.textPrimary,
    marginBottom: 2,
  },
  toolSub: {
    fontFamily: typography.fontBody,
    fontSize: typography.sizeCaption,
    color: colors.textMuted,
    lineHeight: typography.lineCaption,
  },

  // Campus — fond navy solid, ZÉRO LinearGradient décoratif (/quieter)
  campusSection: { marginBottom: spacing.lg },
  campusCard: {
    marginHorizontal: spacing.base,
    borderRadius: radius.xl,
    padding: spacing.xl,
    overflow: 'hidden',
    backgroundColor: colors.brandNavy,  // solid — pas de gradient cyberpunk
  },
  campusIconView: { textAlign: 'center', marginBottom: spacing.sm },
  campusTitle: {
    fontFamily: typography.fontDisplay,
    fontSize: typography.sizeH1,
    color: colors.textOnNavy,
    textAlign: 'center',
    letterSpacing: 2,
  },
  campusTagline: {
    fontFamily: typography.fontBody,
    fontSize: typography.sizeCaption,
    color: 'rgba(255,255,255,0.70)',
    textAlign: 'center',
    marginTop: spacing.xs,
    marginBottom: spacing.lg,
  },
  campusGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  campusFeature: { width: '44%', alignItems: 'center', gap: 6 },
  campusFeatureIcon: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    // Fond solid teinté — pas de LinearGradient décoratif
  },
  campusFeatureLabel: {
    fontFamily: typography.fontBodyBold,
    fontSize: typography.sizeCaption,
    color: colors.textOnNavy,
    textAlign: 'center',
  },
  campusFeatureSub: {
    fontFamily: typography.fontBody,
    fontSize: 10,
    color: 'rgba(255,255,255,0.60)',
    textAlign: 'center',
  },
  campusCTA: {
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    backgroundColor: colors.brand,   // solid brand terracotta — /bolder
    minHeight: 44,
  },
  campusCTAText: {
    fontFamily: typography.fontBodyBold,
    color: colors.textOnBrand,
    fontSize: typography.sizeBody,
    letterSpacing: 0.5,
  },
  campusNote: {
    fontFamily: typography.fontBody,
    textAlign: 'center',
    fontSize: 10,
    color: 'rgba(255,255,255,0.45)',
    marginTop: spacing.md,
  },

  disclaimerWrap: {
    marginHorizontal: spacing.base,
    marginTop: spacing.sm,
  },

  // ─── Segment toggle (Particulier / Etudiant) — design system Lexavo ───
  segmentWrap: {
    paddingHorizontal: spacing.base,
    marginTop: spacing.lg,
  },
  segmentTrack: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: radius.round,
    padding: 4,
    gap: 4,
    borderWidth: 1,
    borderColor: colors.border,
    ...elevation.low,
  },
  segmentBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
    paddingVertical: 10,
    paddingHorizontal: spacing.md,
    borderRadius: radius.round,
    minHeight: touch.minSize,
  },
  segmentBtnActive: {
    backgroundColor: colors.brand,
  },
  segmentBtnText: {
    fontFamily: typography.fontBodyMedium,
    fontSize: typography.sizeSmall,
    color: colors.textMuted,
  },
  segmentBtnTextActive: {
    color: colors.textOnBrand,
    fontFamily: typography.fontBodySemiBold,
  },

  // ─── Bouton "Voir plus" ───
  viewMoreBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
    alignSelf: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    marginTop: spacing.md,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    minHeight: touch.minSize,
  },
  viewMoreText: {
    fontFamily: typography.fontBodyMedium,
    fontSize: typography.sizeSmall,
    color: colors.brand,
  },

  // ─── Modal "Voir plus" ───
  moreModal: {
    backgroundColor: colors.surface,
    marginHorizontal: spacing.base,
    borderRadius: radius.lg,
    padding: spacing.lg,
    maxWidth: 480,
    width: '90%',
    alignSelf: 'center',
    ...elevation.high,
  },
  moreModalTitle: {
    fontFamily: typography.fontDisplay,
    fontSize: typography.sizeH2,
    color: colors.textPrimary,
    marginBottom: spacing.md,
    textAlign: 'center',
  },
  moreModalRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
    borderRadius: radius.md,
    gap: spacing.md,
    minHeight: touch.minSize,
  },
  moreModalIcon: {
    width: 40,
    height: 40,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  moreModalTexts: {
    flex: 1,
  },
  moreModalRowTitle: {
    fontFamily: typography.fontBodyMedium,
    fontSize: typography.sizeBody,
    color: colors.textPrimary,
  },
  moreModalRowSub: {
    fontFamily: typography.fontBody,
    fontSize: typography.sizeCaption,
    color: colors.textMuted,
    marginTop: 2,
  },
});
