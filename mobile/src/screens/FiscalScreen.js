import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { askFiscal } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import ModelBadge from '../components/ModelBadge';
import { LinearGradient } from 'expo-linear-gradient';

const FISCAL_DARK = '#34495E';

const QUICK_QUESTIONS = [
  'Quelles sont les tranches de l\'IPP en 2025 ?',
  'Comment fonctionne la TVA pour un indépendant ?',
  'Quels frais professionnels sont déductibles ?',
  'Qu\'est-ce que l\'ISOC et qui y est soumis ?',
  'Quels sont les délais de prescription fiscale ?',
];

export default function FiscalScreen() {
  const [question, setQuestion] = useState('');
  const [context, setContext]   = useState('');
  const [showCtx, setShowCtx]   = useState(false);
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState(null);
  const [photos, setPhotos] = useState([]);

  const ask = async (q = question) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    setQuestion(trimmed);
    setLoading(true); setResult(null); setError(null);
    try {
      const data = await askFiscal(trimmed, context.trim(), photos);
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

        <LinearGradient colors={['#0F1A2E', '#34495E']} style={styles.heroHeader}>
          <Text style={styles.heroEmoji}>💰</Text>
          <Text style={styles.heroTitle}>Fiscal — Questions fiscales</Text>
          <Text style={styles.heroSub}>IPP, ISOC, TVA · Droit fiscal belge</Text>
        </LinearGradient>

        <View style={styles.card}>
          <Text style={styles.fieldLabel}>Votre question fiscale</Text>
          <TextInput
            style={styles.textArea}
            multiline
            numberOfLines={4}
            placeholder="Ex: Puis-je déduire mes frais de bureau en tant qu'indépendant ?"
            placeholderTextColor={colors.textMuted}
            value={question}
            onChangeText={setQuestion}
            textAlignVertical="top"
            accessibilityLabel="Question fiscale"
          />

          <TouchableOpacity activeOpacity={0.75}
            style={styles.ctxToggle}
            onPress={() => setShowCtx(!showCtx)}
          >
            <Text style={styles.ctxToggleText}>
              {showCtx ? '▲' : '▼'} Contexte supplémentaire
            </Text>
          </TouchableOpacity>

          {showCtx && (
            <TextInput
              style={[styles.textArea, { minHeight: 70, marginTop: 6 }]}
              multiline
              placeholder="Ex: Je suis indépendant complémentaire, revenus ~30.000€/an..."
              placeholderTextColor={colors.textMuted}
              value={context}
              onChangeText={setContext}
              textAlignVertical="top"
              accessibilityLabel="Contexte supplémentaire"
            />
          )}

          <PhotoPicker photos={photos} onPhotosChange={setPhotos} />

            <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, (!question.trim() || loading) && styles.btnDisabled]}
            onPress={() => ask()}
            disabled={!question.trim() || loading}
          >
            {loading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>💰  Analyser</Text>
            }
          </TouchableOpacity>
        </View>

        {/* Quick questions */}
        {!result && !loading && (
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Questions fréquentes</Text>
            {QUICK_QUESTIONS.map((q, i) => (
              <TouchableOpacity activeOpacity={0.75}
                key={i}
                style={styles.quickItem}
                onPress={() => { setQuestion(q); ask(q); }}
              >
                <Text style={styles.quickArrow}>›</Text>
                <Text style={styles.quickText}>{q}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>⚠️ {error}</Text>
          </View>
        )}

        {result && (
          <View style={styles.card}>
            <ModelBadge model={result.model} />
            {/* Answer */}
            {result.answer && (
              <View style={styles.section}>
                <View style={styles.answerHeader}>
                  <Text style={styles.answerHeaderText}>💰 Réponse fiscale</Text>
                </View>
                <Text style={styles.answerText}>{result.answer}</Text>
              </View>
            )}

            {/* Applicable articles */}
            {result.applicable_articles?.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Articles applicables</Text>
                {result.applicable_articles.map((a, i) => (
                  <View key={i} style={styles.articleItem}>
                    <Text style={styles.articleText}>📖 {a}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Tax rates */}
            {result.tax_rates && Object.keys(result.tax_rates).length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Taux applicables</Text>
                {Object.entries(result.tax_rates).map(([k, v]) => (
                  <View key={k} style={styles.rateRow}>
                    <Text style={styles.rateKey}>{k.replace(/_/g, ' ')}</Text>
                    <Text style={styles.rateVal}>{typeof v === 'number' ? `${v}%` : String(v)}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Calculation if any */}
            {result.calculation && (
              <View style={styles.calcBox}>
                <Text style={styles.calcTitle}>Calcul indicatif</Text>
                <Text style={styles.calcText}>{result.calculation}</Text>
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
    marginBottom: 8,
  },

  ctxToggle:     { alignSelf: 'flex-start', marginBottom: 8 },
  ctxToggleText: { fontSize: 12, color: colors.primaryLight, fontWeight: '600' },

  btn: {
    backgroundColor: FISCAL_DARK,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 4,
  },
  btnDisabled: { opacity: 0.45 },
  btnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },

  sectionTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },

  quickItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: 10,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: colors.border,
  },
  quickArrow: { fontSize: 16, color: FISCAL_DARK, marginRight: 8, marginTop: -1 },
  quickText:  { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 18 },

  errorBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#FCA5A5',
    marginBottom: 16,
  },
  errorText: { fontSize: 13, color: colors.error, fontWeight: '600' },

  section: { marginBottom: 14 },

  answerHeader: {
    backgroundColor: FISCAL_DARK,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  answerHeaderText: { color: '#FFF', fontWeight: '700', fontSize: 13 },
  modelBadge: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  modelText: { color: '#FFF', fontSize: 10, fontWeight: '600' },
  answerText: { fontSize: 14, color: colors.textPrimary, lineHeight: 22 },

  articleItem: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 8,
    padding: 9,
    marginBottom: 5,
  },
  articleText: { fontSize: 12, color: colors.textSecondary, lineHeight: 17 },

  rateRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  rateKey: { fontSize: 12, color: colors.textSecondary, flex: 1 },
  rateVal: { fontSize: 12, fontWeight: '700', color: FISCAL_DARK },

  calcBox: {
    backgroundColor: '#F0FDF4',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#BBF7D0',
    marginBottom: 10,
  },
  calcTitle: { fontSize: 11, fontWeight: '700', color: '#065F46', marginBottom: 4 },
  calcText:  { fontSize: 12, color: '#14532D', lineHeight: 18, fontFamily: 'monospace' },

  disclaimer: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic', textAlign: 'center' },
});
