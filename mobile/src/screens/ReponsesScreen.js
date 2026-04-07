import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { generateLegalResponse } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import ModelBadge from '../components/ModelBadge';
import { LinearGradient } from 'expo-linear-gradient';

const REPONSE_PURPLE = '#8E44AD';
const TONES = [
  { id: 'formal',      label: '🎩 Formel',    sub: 'Professionnel' },
  { id: 'firm',        label: '💼 Ferme',      sub: 'Assertif' },
  { id: 'conciliatory', label: '🤝 Amiable',  sub: 'Dialogue' },
];

export default function ReponsesScreen() {
  const [situation, setSituation]       = useState('');
  const [desiredOutcome, setDesired]    = useState('');
  const [tone, setTone]                 = useState('formal');
  const [loading, setLoading]           = useState(false);
  const [result, setResult]             = useState(null);
  const [error, setError]               = useState(null);
  const [photos, setPhotos] = useState([]);

  const generate = async () => {
    if (!situation.trim() || !desiredOutcome.trim()) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const data = await generateLegalResponse(situation.trim(), desiredOutcome.trim(), tone);
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

        <LinearGradient colors={['#4A1D96', '#8E44AD']} style={styles.heroHeader}>
          <Text style={styles.heroEmoji}>✉️</Text>
          <Text style={styles.heroTitle}>Réponses — Lettre juridique</Text>
          <Text style={styles.heroSub}>Générez une réponse formelle en droit belge</Text>
        </LinearGradient>

        <View style={styles.card}>
          <Text style={styles.fieldLabel}>Votre situation</Text>
          <TextInput
            style={styles.textArea}
            multiline
            numberOfLines={4}
            placeholder="Ex: Mon bailleur refuse de me rembourser la garantie locative de 1500€ malgré un état des lieux conforme..."
            placeholderTextColor={colors.textMuted}
            value={situation}
            onChangeText={setSituation}
            textAlignVertical="top"
            accessibilityLabel="Description de la situation"
          />

          <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Ce que vous souhaitez obtenir</Text>
          <TextInput
            style={[styles.textArea, { minHeight: 80 }]}
            multiline
            numberOfLines={3}
            placeholder="Ex: Remboursement immédiat de la garantie + intérêts de retard"
            placeholderTextColor={colors.textMuted}
            value={desiredOutcome}
            onChangeText={setDesired}
            textAlignVertical="top"
            accessibilityLabel="Résultat souhaité"
          />

          <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Ton de la réponse</Text>
          <View style={styles.toneRow}>
            {TONES.map((t) => (
              <TouchableOpacity activeOpacity={0.75}
                key={t.id}
                style={[styles.toneBtn, tone === t.id && styles.toneBtnActive]}
                onPress={() => setTone(t.id)}
              >
                <Text style={[styles.toneLabel, tone === t.id && styles.toneLabelActive]}>{t.label}</Text>
                <Text style={styles.toneSub}>{t.sub}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <PhotoPicker photos={photos} onPhotosChange={setPhotos} label="📷 Photo du courrier" />

          <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, (!situation.trim() || !desiredOutcome.trim() || loading) && styles.btnDisabled]}
            onPress={generate}
            disabled={!situation.trim() || !desiredOutcome.trim() || loading}
          >
            {loading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>✉️  Générer la réponse</Text>
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
            <View style={styles.resultHeader}>
              <Text style={styles.resultTitle}>Réponse générée</Text>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                {result.tone && (
                  <View style={styles.tonePill}>
                    <Text style={styles.tonePillText}>{result.tone}</Text>
                  </View>
                )}
                <ModelBadge model={result.model} style={{ alignSelf: 'center', marginBottom: 0 }} />
              </View>
            </View>

            {result.response_text && (
              <View style={styles.letterBox}>
                <Text style={styles.letterText}>{result.response_text}</Text>
              </View>
            )}

            {result.legal_basis && (
              <View style={styles.legalBox}>
                <Text style={styles.legalText}>📖 {result.legal_basis}</Text>
              </View>
            )}

            {result.next_steps?.length > 0 && (
              <View style={styles.stepsSection}>
                <Text style={styles.stepsTitle}>Prochaines étapes</Text>
                {result.next_steps.map((s, i) => (
                  <View key={i} style={styles.stepItem}>
                    <Text style={styles.stepNum}>{i + 1}</Text>
                    <Text style={styles.stepText}>{s}</Text>
                  </View>
                ))}
              </View>
            )}

            {result.disclaimer && (
              <Text style={styles.disclaimer}>{result.disclaimer}</Text>
            )}
          </View>
        )}
        <View style={{ marginTop: 12, padding: 10, backgroundColor: '#FFFBEB', borderRadius: 8, borderWidth: 1, borderColor: '#FDE68A' }}>
          <Text style={{ fontSize: 10, color: '#92400E', textAlign: 'center', fontStyle: 'italic', lineHeight: 14 }}>
            {'\u2696\ufe0f Lexavo est un outil d\'information juridique. Il ne remplace pas un avocat ni un conseiller juridique professionnel.'}
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

  fieldLabel: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 },
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
  },

  toneRow: { flexDirection: 'row', gap: 8, marginBottom: 14 },
  toneBtn: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 10,
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  toneBtnActive:  { borderColor: REPONSE_PURPLE, backgroundColor: '#F5EEF8' },
  toneLabel:      { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  toneLabelActive: { color: REPONSE_PURPLE },
  toneSub:        { fontSize: 10, color: colors.textMuted, marginTop: 2 },

  btn: {
    backgroundColor: REPONSE_PURPLE,
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

  resultHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  resultTitle:  { fontSize: 14, fontWeight: '700', color: colors.textPrimary },
  tonePill: { backgroundColor: '#F3E8FF', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3 },
  tonePillText: { fontSize: 10, color: REPONSE_PURPLE, fontWeight: '700' },

  letterBox: {
    backgroundColor: '#FAFAFA',
    borderRadius: 10,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 12,
  },
  letterText: { fontSize: 13, color: colors.textPrimary, lineHeight: 20 },

  legalBox: { backgroundColor: colors.surfaceAlt, borderRadius: 8, padding: 10, marginBottom: 12 },
  legalText: { fontSize: 11, color: colors.textSecondary, lineHeight: 16 },

  stepsSection: { marginBottom: 12 },
  stepsTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  stepItem: { flexDirection: 'row', gap: 10, marginBottom: 6, alignItems: 'flex-start' },
  stepNum: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: REPONSE_PURPLE,
    color: '#FFF',
    fontSize: 11,
    fontWeight: '700',
    textAlign: 'center',
    lineHeight: 20,
  },
  stepText: { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 19 },

  disclaimer: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic', textAlign: 'center' },
});
