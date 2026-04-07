import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform, Linking,
} from 'react-native';
import { findMatchingLawyers } from '../api/client';
import { colors } from '../theme/colors';
import ModelBadge from '../components/ModelBadge';
import { LinearGradient } from 'expo-linear-gradient';

const MATCH_BLUE = '#0050A0';

const CITIES = [
  'Bruxelles', 'Liège', 'Gand', 'Anvers', 'Charleroi',
  'Namur', 'Mons', 'Louvain', 'Bruges', 'Hasselt',
];

export default function MatchScreen() {
  const [situation, setSituation] = useState('');
  const [city, setCity]           = useState('');
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState(null);
  const [error, setError]         = useState(null);

  const find = async () => {
    if (!situation.trim()) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const data = await findMatchingLawyers(situation.trim(), city);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        <LinearGradient colors={['#003366', '#0050A0']} style={styles.heroHeader}>
          <Text style={styles.heroEmoji}>🤝</Text>
          <Text style={styles.heroTitle}>Match — Trouver un avocat</Text>
          <Text style={styles.heroSub}>Mis en relation avec l'avocat idéal</Text>
        </LinearGradient>

        <View style={styles.card}>
          <Text style={styles.fieldLabel}>Décrivez votre besoin juridique</Text>
          <TextInput
            style={styles.textArea}
            multiline
            numberOfLines={4}
            placeholder="Ex: J'ai besoin d'un avocat pour un litige locatif à Bruxelles..."
            placeholderTextColor={colors.textMuted}
            value={situation}
            onChangeText={setSituation}
            textAlignVertical="top"
            accessibilityLabel="Besoin juridique"
          />

          <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Ville (optionnel)</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.cityScroll}>
            {['', ...CITIES].map((c) => (
              <TouchableOpacity activeOpacity={0.75}
                key={c}
                style={[styles.cityChip, city === c && styles.cityChipActive]}
                onPress={() => setCity(c)}
              >
                <Text style={[styles.cityLabel, city === c && styles.cityLabelActive]}>
                  {c === '' ? '📍 Toutes' : c}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, (!situation.trim() || loading) && styles.btnDisabled]}
            onPress={find}
            disabled={!situation.trim() || loading}
          >
            {loading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>🤝  Trouver un avocat</Text>
            }
          </TouchableOpacity>
        </View>

        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>⚠️ {error}</Text>
          </View>
        )}

        {result && (
          <View>
            <ModelBadge model={result.model} />
            {result.detected_branch && (
              <View style={styles.branchBox}>
                <Text style={styles.branchLabel}>Branche du droit détectée</Text>
                <Text style={styles.branchValue}>{result.detected_branch}</Text>
              </View>
            )}

            {result.lawyers?.length > 0 ? (
              result.lawyers.map((lawyer, i) => (
                <View key={i} style={[styles.lawyerCard, i === 0 && styles.lawyerCardTop]}>
                  {i === 0 && (
                    <View style={styles.topBadge}>
                      <Text style={styles.topBadgeText}>⭐ Meilleur match</Text>
                    </View>
                  )}
                  <View style={styles.lawyerHeader}>
                    <View style={styles.lawyerAvatar}>
                      <Text style={styles.lawyerAvatarText}>{lawyer.name?.[0] ?? '?'}</Text>
                    </View>
                    <View style={styles.lawyerInfo}>
                      <Text style={styles.lawyerName}>{lawyer.name}</Text>
                      <Text style={styles.lawyerSpec}>{lawyer.specialty}</Text>
                    </View>
                    {lawyer.match_score != null && (
                      <Text style={styles.matchScore}>{(lawyer.match_score * 100).toFixed(0)}%</Text>
                    )}
                  </View>
                  {lawyer.city && (
                    <Text style={styles.lawyerCity}>📍 {lawyer.city}</Text>
                  )}
                  {lawyer.languages?.length > 0 && (
                    <Text style={styles.lawyerLang}>🌐 {lawyer.languages.join(' · ')}</Text>
                  )}
                  {lawyer.bio && (
                    <Text style={styles.lawyerBio} numberOfLines={2}>{lawyer.bio}</Text>
                  )}
                  <View style={styles.lawyerActions}>
                    <TouchableOpacity activeOpacity={0.75}
                      style={styles.contactBtn}
                      onPress={() => {
                        if (lawyer.phone) Linking.openURL('tel:' + lawyer.phone);
                        else if (lawyer.email) Linking.openURL('mailto:' + lawyer.email);
                      }}
                    >
                      <Text style={styles.contactBtnText}>📞 Contacter</Text>
                    </TouchableOpacity>
                    {lawyer.first_consultation === 'free' && (
                      <View style={styles.freePill}>
                        <Text style={styles.freePillText}>1ère consultation gratuite</Text>
                      </View>
                    )}
                  </View>
                </View>
              ))
            ) : (
              <View style={styles.noResultBox}>
                <Text style={styles.noResultText}>Aucun avocat trouvé pour ces critères.</Text>
              </View>
            )}

            <View style={{ marginTop: 12, padding: 10, backgroundColor: '#FFFBEB', borderRadius: 8, borderWidth: 1, borderColor: '#FDE68A' }}>
              <Text style={{ fontSize: 10, color: '#92400E', textAlign: 'center', fontStyle: 'italic', lineHeight: 14 }}>
                ⚖️ Lexavo est un outil d'information juridique. Il ne remplace pas un avocat ni un conseiller juridique professionnel.
              </Text>
            </View>
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content:   { padding: 16, paddingBottom: 40 },

  heroHeader: { borderRadius: 16, padding: 20, marginBottom: 16, alignItems: 'center' },
  heroEmoji: { fontSize: 32, marginBottom: 8 },
  heroTitle: { fontSize: 20, fontWeight: '900', color: '#FFF', letterSpacing: 0.5 },
  heroSub: { fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4, textAlign: 'center' },

  card: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    elevation: 3,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 1,
  },
  featureHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 14 },
  featureEmoji:  { fontSize: 28 },
  featureTitle:  { fontSize: 15, fontWeight: '700', color: colors.textPrimary },
  featureSub:    { fontSize: 12, color: colors.textMuted, marginTop: 1 },

  fieldLabel: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  textArea: {
    backgroundColor: colors.background,
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    color: colors.textPrimary,
    minHeight: 100,
    borderWidth: 1,
    borderColor: colors.border,
    lineHeight: 20,
    marginBottom: 4,
  },

  cityScroll: { marginBottom: 12 },
  cityChip: {
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 6,
    backgroundColor: colors.background,
  },
  cityChipActive: { backgroundColor: MATCH_BLUE, borderColor: MATCH_BLUE },
  cityLabel: { fontSize: 12, color: colors.textSecondary },
  cityLabelActive: { color: '#FFF', fontWeight: '700' },

  btn: {
    backgroundColor: MATCH_BLUE,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  btnDisabled: { opacity: 0.45 },
  btnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },

  errorBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#FCA5A5',
    marginBottom: 16,
  },
  errorText: { fontSize: 13, color: colors.error, fontWeight: '600' },

  branchBox: {
    backgroundColor: '#EFF6FF',
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#BFDBFE',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  branchLabel: { fontSize: 11, color: colors.textMuted },
  branchValue: { fontSize: 13, fontWeight: '700', color: MATCH_BLUE },

  lawyerCard: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 14,
    marginBottom: 12,
    elevation: 2,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 1,
    borderWidth: 1,
    borderColor: colors.border,
  },
  lawyerCardTop: { borderColor: MATCH_BLUE, borderWidth: 2 },

  topBadge: {
    backgroundColor: '#EFF6FF',
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
    alignSelf: 'flex-start',
    marginBottom: 8,
  },
  topBadgeText: { fontSize: 10, color: MATCH_BLUE, fontWeight: '700' },

  lawyerHeader: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 6 },
  lawyerAvatar: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: MATCH_BLUE,
    alignItems: 'center',
    justifyContent: 'center',
  },
  lawyerAvatarText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
  lawyerInfo:  { flex: 1 },
  lawyerName:  { fontSize: 14, fontWeight: '700', color: colors.textPrimary },
  lawyerSpec:  { fontSize: 11, color: colors.textMuted },
  matchScore:  { fontSize: 14, fontWeight: '800', color: MATCH_BLUE },

  lawyerCity: { fontSize: 12, color: colors.textSecondary, marginBottom: 2 },
  lawyerLang: { fontSize: 11, color: colors.textMuted, marginBottom: 4 },
  lawyerBio:  { fontSize: 12, color: colors.textSecondary, lineHeight: 17, marginBottom: 8 },

  lawyerActions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  contactBtn: {
    backgroundColor: MATCH_BLUE,
    borderRadius: 8,
    paddingVertical: 7,
    paddingHorizontal: 14,
  },
  contactBtnText: { color: '#FFF', fontSize: 12, fontWeight: '700' },
  freePill: {
    backgroundColor: '#D1FAE5',
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  freePillText: { fontSize: 10, color: '#065F46', fontWeight: '600' },

  noResultBox: { padding: 24, alignItems: 'center' },
  noResultText: { fontSize: 13, color: colors.textMuted },

  disclaimer: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic', textAlign: 'center', marginTop: 8 },
});
