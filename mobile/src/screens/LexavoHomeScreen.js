import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, StatusBar,
} from 'react-native';
import { colors } from '../theme/colors';

const LEXAVO_ORANGE = '#C45A2D';
const LEXAVO_NAVY   = '#1C2B3A';

const FEATURES = [
  { id: 'Defend',       emoji: '⚡', title: 'Defend',        sub: 'Contestez, reclamez, agissez',   color: '#C45A2D', screen: 'Defend' },
  { id: 'Document',     emoji: '📄', title: 'Document',      sub: 'Analyser un document',           color: '#C0392B', screen: 'Shield' },
  { id: 'Calculateurs', emoji: '🧮', title: 'Calculateurs',  sub: 'Preavis, pension, succession',   color: '#27AE60', screen: 'Calculateurs' },
  { id: 'Contrats',     emoji: '📝', title: 'Contrats',      sub: 'Generation de contrats PDF',     color: '#2980B9', screen: 'Contrats' },
  { id: 'Reponses',     emoji: '✉️', title: 'Reponses',      sub: 'Reponse juridique formelle',     color: '#8E44AD', screen: 'Reponses' },
  { id: 'Diagnostic',   emoji: '🔬', title: 'Diagnostic',    sub: 'Analyse multi-branches',         color: LEXAVO_ORANGE, screen: 'Diagnostic' },
  { id: 'Score',        emoji: '📊', title: 'Score juridique', sub: 'Sante juridique sur 100',      color: '#F39C12', screen: 'Score' },
  { id: 'AuditEntreprise', emoji: '🏢', title: 'Audit Entreprise', sub: 'Audit rapide ou approfondi', color: '#16A085', screen: 'Compliance' },
  { id: 'Alertes',      emoji: '🔔', title: 'Alertes',       sub: 'Veille legislative belge',       color: '#D4A017', screen: 'Alertes' },
  { id: 'Litiges',      emoji: '⚖️', title: 'Litiges',       sub: 'Recouvrement impayes',           color: '#B22222', screen: 'Litiges' },
  { id: 'Match',        emoji: '🤝', title: 'Match',         sub: 'Trouver l\'avocat ideal',        color: '#0050A0', screen: 'Match' },
  { id: 'Emergency',    emoji: '🚨', title: 'Emergency',     sub: 'Urgence juridique — 24h',        color: '#E74C3C', screen: 'Emergency' },
  { id: 'Proof',        emoji: '🗂️', title: 'Proof',         sub: 'Constituer un dossier de preuves', color: '#1A6B3A', screen: 'Proof' },
  { id: 'Heritage',     emoji: '🏛️', title: 'Heritage',      sub: 'Guide successoral belge',        color: '#8B4513', screen: 'Heritage' },
  { id: 'Fiscal',       emoji: '💰', title: 'Fiscal',        sub: 'Questions fiscales belges',      color: '#34495E', screen: 'Fiscal' },
];

export default function LexavoHomeScreen({ navigation }) {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <StatusBar barStyle="light-content" backgroundColor={LEXAVO_NAVY} />

      {/* Hero */}
      <View style={styles.hero}>
        <Text style={styles.heroMark}>LEXAVO</Text>
        <Text style={styles.heroSub}>L'assistant juridique belge</Text>
        <View style={styles.heroPill}>
          <Text style={styles.heroPillText}>Droit belge · 8 langues</Text>
        </View>
      </View>

      {/* Grid */}
      <View style={styles.grid}>
        {FEATURES.map((f) => (
          <TouchableOpacity activeOpacity={0.75}
            key={f.id}
            style={[styles.card, { borderTopColor: f.color }]}
            onPress={() => navigation.navigate(f.screen)}
            activeOpacity={0.78}
          >
            <Text style={styles.cardEmoji}>{f.emoji}</Text>
            <Text style={styles.cardTitle}>{f.title}</Text>
            <Text style={styles.cardSub}>{f.sub}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.disclaimer}>
        <Text style={styles.disclaimerText}>
          Lexavo est un assistant juridique. Il ne remplace pas un avocat ou un conseiller juridique.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content:   { paddingBottom: 40 },

  hero: {
    backgroundColor: LEXAVO_NAVY,
    paddingTop: 50,
    paddingBottom: 28,
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  heroMark: {
    fontSize: 30,
    fontWeight: '900',
    color: LEXAVO_ORANGE,
    letterSpacing: 6,
    marginBottom: 4,
  },
  heroSub: { fontSize: 13, color: 'rgba(255,255,255,0.7)', marginBottom: 12 },
  heroPill: {
    backgroundColor: 'rgba(255,255,255,0.12)',
    paddingHorizontal: 14,
    paddingVertical: 5,
    borderRadius: 20,
  },
  heroPillText: { color: '#FFF', fontSize: 11, fontWeight: '600' },

  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 12,
    gap: 10,
  },
  card: {
    width: '47%',
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 14,
    borderTopWidth: 3,
    elevation: 3,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 1,
  },
  cardEmoji: { fontSize: 24, marginBottom: 6 },
  cardTitle: { fontSize: 14, fontWeight: '700', color: colors.textPrimary, marginBottom: 3 },
  cardSub:   { fontSize: 11, color: colors.textMuted, lineHeight: 15 },

  disclaimer: {
    marginHorizontal: 16,
    marginTop: 8,
    padding: 10,
    backgroundColor: '#FFFBEB',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#FDE68A',
  },
  disclaimerText: {
    fontSize: 10,
    color: '#92400E',
    textAlign: 'center',
    fontStyle: 'italic',
    lineHeight: 14,
  },
});
