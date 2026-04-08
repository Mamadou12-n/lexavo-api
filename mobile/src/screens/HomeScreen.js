import React, { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  RefreshControl, StatusBar,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect } from '@react-navigation/native';
import { getSubscriptionStatus } from '../api/client';
import { colors } from '../theme/colors';

const LEXAVO_ORANGE = '#C45A2D';
const LEXAVO_NAVY   = '#1C2B3A';

const TOOLS = [
  { emoji: '⚡', title: 'Contester', sub: 'Contester une décision', color: '#C45A2D', screen: 'Defend' },
  { emoji: '📄', title: 'Document', sub: 'Analyser un contrat', color: '#C0392B', screen: 'Shield' },
  { emoji: '🔬', title: 'Diagnostic', sub: 'Comprendre ma situation', color: '#8E44AD', screen: 'Diagnostic' },
  { emoji: '🧮', title: 'Calculateurs', sub: 'Préavis · Pension · Succession', color: '#1A6B8A', screen: 'Calculateurs' },
  { emoji: '🤝', title: 'Avocat', sub: 'Trouver un avocat', color: '#0050A0', screen: 'Match' },
  { emoji: '🚨', title: 'Urgence', sub: 'Avocat en 24h — 49€', color: '#E74C3C', screen: 'Emergency' },
  { emoji: '💰', title: 'Fiscal', sub: 'Questions fiscales', color: '#34495E', screen: 'Fiscal' },
];


export default function HomeScreen({ navigation }) {
  const [quota, setQuota]           = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try { setQuota(await getSubscriptionStatus()); } catch (_) {}
    setRefreshing(false);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const goTool = (screen) => navigation.navigate('Outils', { screen });

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor={LEXAVO_ORANGE} />}
    >
      <StatusBar barStyle="light-content" backgroundColor={LEXAVO_NAVY} />

      {/* ═══ HERO ═══ */}
      <View style={styles.hero}>
        <Text style={styles.heroMark}>LEXAVO</Text>
        <Text style={styles.heroTagline}>ASSISTANT JURIDIQUE BELGE</Text>
        <Text style={styles.heroSub}>Le droit pour tous</Text>
        <View style={styles.heroPill}>
          <View style={styles.pulseDot} />
          <Text style={styles.heroPillText}>Outils juridiques · Droit belge · 8 langues</Text>
        </View>
      </View>

      {/* ═══ 2 GRANDES CARTES ═══ */}
      <View style={styles.dualCards}>
        <TouchableOpacity
          activeOpacity={0.75}
          style={styles.bigCardBlue}
          onPress={() => navigation.navigate('Ask')}
        >
          <Text style={styles.bigCardEmoji}>💬</Text>
          <Text style={styles.bigCardTitle}>Je veux comprendre</Text>
          <Text style={styles.bigCardSub}>Chat IA juridique</Text>
        </TouchableOpacity>
        <TouchableOpacity
          activeOpacity={0.75}
          style={styles.bigCardOrange}
          onPress={() => navigation.navigate('Outils', { screen: 'Defend' })}
        >
          <Text style={styles.bigCardEmoji}>⚡</Text>
          <Text style={styles.bigCardTitle}>Je veux agir</Text>
          <Text style={styles.bigCardSub}>Contester / Recours</Text>
        </TouchableOpacity>
      </View>

      {/* ═══ LEXAVO CAMPUS ═══ */}
      <View style={styles.campusSection}>
        <LinearGradient
          colors={['#0A1628', '#0F1F3D', '#1A0A3E']}
          start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
          style={styles.campusCard}
        >
          {/* Header avec glow effect */}
          <View style={styles.campusGlow} />
          <Text style={styles.campusIcon}>{'\u{1F9EC}'}</Text>
          <Text style={styles.campusTitle}>LEXAVO CAMPUS</Text>
          <Text style={styles.campusTagline}>Le droit belge, version next-gen</Text>

          {/* 4 features en grille 2x2 avec icones neon */}
          <View style={styles.campusGrid}>
            <View style={styles.campusFeature}>
              <LinearGradient colors={['#6C3FA0', '#8B5CF6']} style={styles.campusFeatureIcon}>
                <Text style={{ fontSize: 18 }}>{'\u26A1'}</Text>
              </LinearGradient>
              <Text style={styles.campusFeatureLabel}>Quiz IA</Text>
              <Text style={styles.campusFeatureSub}>Adaptatif</Text>
            </View>
            <View style={styles.campusFeature}>
              <LinearGradient colors={['#008060', '#00D4AA']} style={styles.campusFeatureIcon}>
                <Text style={{ fontSize: 18 }}>{'\u{1F916}'}</Text>
              </LinearGradient>
              <Text style={styles.campusFeatureLabel}>Tuteur IA</Text>
              <Text style={styles.campusFeatureSub}>24/7</Text>
            </View>
            <View style={styles.campusFeature}>
              <LinearGradient colors={['#CC7A00', '#FFB84D']} style={styles.campusFeatureIcon}>
                <Text style={{ fontSize: 18 }}>{'\u{1F399}\uFE0F'}</Text>
              </LinearGradient>
              <Text style={styles.campusFeatureLabel}>NotebookLM</Text>
              <Text style={styles.campusFeatureSub}>Podcast IA</Text>
            </View>
            <View style={styles.campusFeature}>
              <LinearGradient colors={['#0068D6', '#4DA6FF']} style={styles.campusFeatureIcon}>
                <Text style={{ fontSize: 18 }}>{'\u{1F4F7}'}</Text>
              </LinearGradient>
              <Text style={styles.campusFeatureLabel}>OCR Notes</Text>
              <Text style={styles.campusFeatureSub}>Photo {'\u2192'} IA</Text>
            </View>
          </View>

          {/* CTA Button gradient */}
          <TouchableOpacity
            activeOpacity={0.85}
            onPress={() => navigation.navigate('Campus')}
          >
            <LinearGradient
              colors={['#00D4AA', '#00B894']}
              start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
              style={styles.campusCTA}
            >
              <Text style={styles.campusCTAText}>{'\u{1F680}'} Acc{'\u00E9'}der {'\u00E0'} Campus</Text>
            </LinearGradient>
          </TouchableOpacity>

          <Text style={styles.campusNote}>Gratuit {'\u00B7'} IA + OCR + Podcast {'\u00B7'} Droit belge</Text>
        </LinearGradient>
      </View>

      {/* ═══ OUTILS JURIDIQUES ═══ */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Outils juridiques</Text>
        <View style={styles.grid}>
          {TOOLS.map((t) => (
            <TouchableOpacity
              activeOpacity={0.75}
              key={t.screen}
              style={styles.toolCard}
              onPress={() => goTool(t.screen)}
            >
              <View style={[styles.toolIcon, { backgroundColor: t.color + '18' }]}>
                <Text style={{ fontSize: 22 }}>{t.emoji}</Text>
              </View>
              <Text style={styles.toolTitle}>{t.title}</Text>
              <Text style={styles.toolSub}>{t.sub}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* ═══ DISCLAIMER ═══ */}
      <View style={styles.disclaimer}>
        <Text style={styles.disclaimerText}>
          ⚖️ Lexavo est un outil d'information juridique. Il ne remplace pas un avocat.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F8FC' },
  content:   { paddingBottom: 40 },

  // Hero
  hero: {
    backgroundColor: LEXAVO_NAVY,
    paddingTop: 48,
    paddingBottom: 28,
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  heroMark: {
    fontSize: 32,
    fontWeight: '900',
    color: LEXAVO_ORANGE,
    letterSpacing: 6,
    marginBottom: 4,
  },
  heroTagline: {
    fontSize: 10,
    color: 'rgba(255,255,255,0.4)',
    fontWeight: '500',
    letterSpacing: 1.5,
    textTransform: 'uppercase',
    marginBottom: 2,
  },
  heroSub: { fontSize: 14, color: 'rgba(255,255,255,0.65)', fontStyle: 'italic', marginBottom: 12 },
  heroPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.08)',
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 8,
  },
  pulseDot: {
    width: 6, height: 6, borderRadius: 3,
    backgroundColor: '#10B981',
  },
  heroPillText: { color: 'rgba(255,255,255,0.7)', fontSize: 11, fontWeight: '600' },

  // 2 grandes cartes
  dualCards: {
    flexDirection: 'row',
    gap: 12,
    padding: 16,
    paddingBottom: 8,
  },
  bigCardBlue: {
    flex: 1,
    backgroundColor: LEXAVO_NAVY,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
  },
  bigCardOrange: {
    flex: 1,
    backgroundColor: LEXAVO_ORANGE,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
  },
  bigCardEmoji: { fontSize: 32, marginBottom: 8 },
  bigCardTitle: { color: '#FFF', fontSize: 15, fontWeight: '700', textAlign: 'center', marginBottom: 4 },
  bigCardSub: { color: 'rgba(255,255,255,0.6)', fontSize: 12, textAlign: 'center' },

  // Section
  section: { paddingHorizontal: 16, paddingTop: 12, marginBottom: 20 },
  sectionTitle: { fontSize: 15, fontWeight: '700', color: '#0F1A2E', marginBottom: 10 },

  // Group title (pour les pages horizontales)
  groupTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: LEXAVO_ORANGE,
    marginBottom: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },

  // Dots pagination
  dots: { flexDirection: 'row', justifyContent: 'center', marginTop: 12, gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#D1D5DB' },
  dotActive: { backgroundColor: LEXAVO_ORANGE, width: 20 },

  // Grid outils (2 colonnes dans chaque page)
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  toolCard: {
    width: '47.5%',
    backgroundColor: '#FFF',
    borderRadius: 14,
    padding: 14,
    overflow: 'hidden',
    elevation: 2,
    shadowColor: 'rgba(15,25,46,0.06)',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 1,
  },
  toolIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  toolTitle: { fontSize: 13, fontWeight: '700', color: '#0F1A2E', marginBottom: 2 },
  toolSub: { fontSize: 11, color: '#94A3B8', lineHeight: 15 },

  // Branches
  branchWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    paddingBottom: 16,
  },
  branchChip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#FFF',
    borderWidth: 1,
    borderColor: '#E8ECF4',
  },
  branchText: { fontSize: 12, color: '#4A5568', fontWeight: '500' },

  // Campus
  campusSection: { marginBottom: 20 },
  campusCard: { marginHorizontal: 16, borderRadius: 20, padding: 24, overflow: 'hidden', position: 'relative' },
  campusGlow: { position: 'absolute', top: -50, right: -50, width: 150, height: 150, borderRadius: 75, backgroundColor: 'rgba(0,212,170,0.08)' },
  campusIcon: { fontSize: 36, textAlign: 'center', marginBottom: 8 },
  campusTitle: { fontSize: 22, fontWeight: '900', color: '#FFF', textAlign: 'center', letterSpacing: 2 },
  campusTagline: { fontSize: 12, color: 'rgba(255,255,255,0.5)', textAlign: 'center', marginTop: 4, marginBottom: 20 },
  campusGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, justifyContent: 'center', marginBottom: 20 },
  campusFeature: { width: (SCREEN_WIDTH - 100) / 2, alignItems: 'center', gap: 6 },
  campusFeatureIcon: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  campusFeatureLabel: { fontSize: 12, fontWeight: '800', color: '#FFF' },
  campusFeatureSub: { fontSize: 10, color: 'rgba(255,255,255,0.45)' },
  campusSearch: { backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: 12, paddingHorizontal: 16, paddingVertical: 12, fontSize: 13, color: '#FFF', borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)', marginBottom: 16 },
  campusCTA: { borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  campusCTAText: { color: '#FFF', fontSize: 15, fontWeight: '900', letterSpacing: 0.5 },
  campusNote: { textAlign: 'center', fontSize: 10, color: 'rgba(255,255,255,0.35)', marginTop: 12 },

  // Disclaimer
  disclaimer: {
    marginHorizontal: 16,
    padding: 12,
    backgroundColor: '#FFFBEB',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#FDE68A',
  },
  disclaimerText: {
    fontSize: 11,
    color: '#92400E',
    textAlign: 'center',
    lineHeight: 16,
  },
});
