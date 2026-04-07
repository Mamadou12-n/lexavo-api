import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { runDiagnostic } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import ModelBadge from '../components/ModelBadge';
import { LinearGradient } from 'expo-linear-gradient';

const DIAG_ORANGE = '#C45A2D';

const USER_TYPES = [
  { id: 'particulier', label: '👤 Particulier' },
  { id: 'independant', label: '💼 Indépendant' },
  { id: 'entreprise',  label: '🏢 Entreprise' },
];

export default function DiagnosticScreen() {
  const [problem, setProblem]   = useState('');
  const [userType, setUserType] = useState('particulier');
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState(null);
  const [photos, setPhotos] = useState([]);

  const analyze = async () => {
    if (!problem.trim()) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const data = await runDiagnostic(problem.trim(), userType);
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

        <LinearGradient colors={['#7C2D12', '#C45A2D']} style={styles.heroHeader}>
          <Text style={styles.heroEmoji}>🔬</Text>
          <Text style={styles.heroTitle}>Diagnostic juridique</Text>
          <Text style={styles.heroSub}>Analyse multi-branches du droit belge</Text>
        </LinearGradient>

        <View style={styles.card}>
          <Text style={styles.fieldLabel}>Votre profil</Text>
          <View style={styles.typeRow}>
            {USER_TYPES.map((t) => (
              <TouchableOpacity activeOpacity={0.75}
                key={t.id}
                style={[styles.typeBtn, userType === t.id && styles.typeBtnActive]}
                onPress={() => setUserType(t.id)}
              >
                <Text style={[styles.typeLabel, userType === t.id && styles.typeLabelActive]}>
                  {t.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Décrivez votre problème juridique</Text>
          <TextInput
            style={styles.textArea}
            multiline
            numberOfLines={6}
            placeholder="Décrivez votre situation en détail : contexte, parties impliquées, événements, documents disponibles..."
            placeholderTextColor={colors.textMuted}
            value={problem}
            onChangeText={setProblem}
            textAlignVertical="top"
            accessibilityLabel="Description du problème juridique"
          />

          <PhotoPicker photos={photos} onPhotosChange={setPhotos} />

            <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, (!problem.trim() || loading) && styles.btnDisabled]}
            onPress={analyze}
            disabled={!problem.trim() || loading}
          >
            {loading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>🔬  Lancer le diagnostic</Text>
            }
          </TouchableOpacity>
        </View>

        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>⚠️ {error}</Text>
          </View>
        )}

        {result && (
          <View style={styles.card}>
            <ModelBadge model={result.model} />
            {/* Branches du droit */}
            {result.branches?.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Branches du droit concernées</Text>
                <View style={styles.branchRow}>
                  {result.branches.map((b, i) => (
                    <View key={i} style={styles.branchPill}>
                      <Text style={styles.branchText}>{b}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {/* Situation summary */}
            {result.situation_summary && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Analyse de la situation</Text>
                <Text style={styles.bodyText}>{result.situation_summary}</Text>
              </View>
            )}

            {/* Applicable law */}
            {result.applicable_law?.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Droit applicable</Text>
                {result.applicable_law.map((l, i) => (
                  <View key={i} style={styles.listItem}>
                    <Text style={styles.bullet}>⚖️</Text>
                    <Text style={styles.listText}>{l}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Recommended steps */}
            {result.recommended_steps?.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Étapes recommandées</Text>
                {result.recommended_steps.map((s, i) => (
                  <View key={i} style={styles.stepItem}>
                    <View style={styles.stepNumCircle}>
                      <Text style={styles.stepNum}>{i + 1}</Text>
                    </View>
                    <Text style={styles.stepText}>{typeof s === 'string' ? s : s.description}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Urgency */}
            {result.urgency_level && (
              <View style={[styles.urgencyBox, { borderColor: result.urgency_level === 'high' ? colors.error : colors.warning }]}>
                <Text style={styles.urgencyText}>
                  {result.urgency_level === 'high' ? '🚨' : result.urgency_level === 'medium' ? '⚠️' : 'ℹ️'} Urgence : {result.urgency_level}
                </Text>
              </View>
            )}

            {result.disclaimer && (
              <Text style={styles.disclaimer}>{result.disclaimer}</Text>
            )}
          </View>
        )}

        <View style={{ marginTop: 12, padding: 10, backgroundColor: '#FFFBEB', borderRadius: 8, borderWidth: 1, borderColor: '#FDE68A' }}>
          <Text style={{ fontSize: 10, color: '#92400E', textAlign: 'center', fontStyle: 'italic', lineHeight: 14 }}>
            ⚖️ Lexavo est un outil d'information juridique. Il ne remplace pas un avocat ni un conseiller juridique professionnel.
          </Text>
        </View>
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

  typeRow: { flexDirection: 'row', gap: 8 },
  typeBtn: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 10,
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  typeBtnActive:  { borderColor: DIAG_ORANGE, backgroundColor: '#FFF7F5' },
  typeLabel:      { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  typeLabelActive: { color: DIAG_ORANGE },

  textArea: {
    backgroundColor: colors.background,
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    color: colors.textPrimary,
    minHeight: 130,
    borderWidth: 1,
    borderColor: colors.border,
    lineHeight: 20,
    marginBottom: 12,
  },

  btn: {
    backgroundColor: DIAG_ORANGE,
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

  section:      { marginBottom: 14 },
  sectionTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  bodyText:     { fontSize: 14, color: colors.textPrimary, lineHeight: 21 },

  branchRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  branchPill: {
    backgroundColor: '#FFF7F5',
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderWidth: 1,
    borderColor: '#FCCBB9',
  },
  branchText: { fontSize: 11, color: DIAG_ORANGE, fontWeight: '600' },

  listItem: { flexDirection: 'row', gap: 8, marginBottom: 6, alignItems: 'flex-start' },
  bullet:   { fontSize: 13, marginTop: 1 },
  listText: { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 19 },

  stepItem: { flexDirection: 'row', gap: 10, marginBottom: 8, alignItems: 'flex-start' },
  stepNumCircle: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: DIAG_ORANGE,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepNum:  { color: '#FFF', fontSize: 11, fontWeight: '700' },
  stepText: { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 19 },

  urgencyBox: {
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    marginBottom: 12,
    backgroundColor: '#FFFBEB',
  },
  urgencyText: { fontSize: 13, fontWeight: '600', color: colors.textPrimary },

  disclaimer: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic', textAlign: 'center' },
});
