/**
 * ShieldScreen → DocumentScreen — Analyseur de documents
 * Fusionne Shield (analyse contrat) + Decode (document admin) en un seul ecran.
 * Toggle "Contrat" vs "Document admin" pour choisir le mode.
 */

import React, { useState, useCallback } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { shieldAnalyze, decodeDocument, REGION_KEY } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import { LinearGradient } from 'expo-linear-gradient';

// ── Shield config ────────────────────────────────────────────────────────────
const VERDICT_CONFIG = {
  green:  { color: '#10B981', bg: '#ECFDF5', label: 'Conforme',        icon: '🟢' },
  orange: { color: '#F59E0B', bg: '#FFFBEB', label: 'Attention requise', icon: '🟠' },
  red:    { color: '#EF4444', bg: '#FEF2F2', label: 'Risque eleve',     icon: '🔴' },
};

const CONTRACT_TYPES = [
  { id: null,          label: 'Auto-detect' },
  { id: 'bail',        label: 'Bail' },
  { id: 'travail',     label: 'Travail' },
  { id: 'vente',       label: 'Vente' },
  { id: 'prestation',  label: 'Prestation' },
  { id: 'nda',         label: 'NDA' },
  { id: 'cgv',         label: 'CGV/CGU' },
  { id: 'licence',     label: 'Licence' },
  { id: 'association', label: 'ASBL' },
  { id: 'mandat',      label: 'Mandat' },
  { id: 'pret',        label: 'Pret' },
];

// ── Decode config ────────────────────────────────────────────────────────────
const URGENCY_COLOR = { critical: '#E74C3C', high: '#E67E22', medium: '#F39C12', low: '#27AE60' };
const URGENCY_LABEL = { critical: '🚨 Critique', high: '⚠️ Urgent', medium: '📋 Modere', low: 'ℹ️ Information' };

const MODE_CONTRACT = 'contract';
const MODE_DOCUMENT = 'document';

export default function ShieldScreen() {
  const [mode, setMode] = useState(MODE_CONTRACT);

  // Shared state
  const [text, setText]       = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState(null);
  const [error, setError]     = useState(null);
  const [photos, setPhotos]   = useState([]);

  // Shield-specific
  const [contractType, setContractType] = useState(null);
  const [history, setHistory]           = useState([]);
  const [showHistory, setShowHistory]   = useState(false);

  // Charger l'historique local au focus (Shield)
  useFocusEffect(
    useCallback(() => {
      AsyncStorage.getItem('@lexavo_shield_history')
        .then(data => { if (data) setHistory(JSON.parse(data)); })
        .catch(() => {});
    }, [])
  );

  // Reset result when switching mode
  const switchMode = (newMode) => {
    if (newMode !== mode) {
      setMode(newMode);
      setResult(null);
      setError(null);
    }
  };

  // ── Shield analyze ─────────────────────────────────────────────────────────
  const analyzeContract = async () => {
    if (text.trim().length < 50) {
      setError('Le contrat doit contenir au moins 50 caracteres.');
      return;
    }
    setLoading(true); setResult(null); setError(null);
    try {
      const region = await AsyncStorage.getItem(REGION_KEY);
      const data = await shieldAnalyze({
        contract_text: text.trim(),
        contract_type: contractType,
        region: region || null,
        photos_base64: photos.map(p => p.base64).filter(Boolean),
      });
      setResult(data);

      const entry = {
        id: Date.now(),
        verdict: data.verdict,
        score: data.score,
        summary: data.summary,
        type: data.contract_type_detected,
        date: new Date().toISOString(),
      };
      const updated = [entry, ...history].slice(0, 10);
      setHistory(updated);
      AsyncStorage.setItem('@lexavo_shield_history', JSON.stringify(updated));
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur reseau');
    } finally {
      setLoading(false);
    }
  };

  // ── Decode analyze ─────────────────────────────────────────────────────────
  const analyzeDocument = async () => {
    if (!text.trim()) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const data = await decodeDocument(text.trim(), 'fr', photos);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur reseau');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = () => {
    if (mode === MODE_CONTRACT) analyzeContract();
    else analyzeDocument();
  };

  const verdict = result && mode === MODE_CONTRACT
    ? VERDICT_CONFIG[result.verdict] || VERDICT_CONFIG.orange
    : null;

  const minLength = mode === MODE_CONTRACT ? 50 : 1;
  const isDisabled = text.trim().length < minLength || loading;

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        {/* Header */}
        <LinearGradient colors={['#8B1A1A', '#C0392B']} style={styles.heroHeader}>
          <View style={{ flexDirection: 'row', alignItems: 'center', width: '100%' }}>
            <View style={{ flex: 1, alignItems: 'center' }}>
              <Text style={styles.heroEmoji}>📄</Text>
              <Text style={styles.heroTitle}>Analyseur de documents</Text>
              <Text style={styles.heroSub}>
                {mode === MODE_CONTRACT
                  ? 'Verdict feu tricolore clause par clause'
                  : 'Dechiffrer un document administratif'}
              </Text>
            </View>
            {mode === MODE_CONTRACT && (
              <TouchableOpacity activeOpacity={0.75} onPress={() => setShowHistory(!showHistory)} style={{ position: 'absolute', right: 0, top: 0 }}>
                <Text style={styles.historyBtn}>📋 {history.length}</Text>
              </TouchableOpacity>
            )}
          </View>
        </LinearGradient>

        {/* Toggle mode */}
        <View style={styles.toggleRow}>
          <TouchableOpacity activeOpacity={0.75}
            style={[styles.toggleBtn, mode === MODE_CONTRACT && styles.toggleBtnActive]}
            onPress={() => switchMode(MODE_CONTRACT)}
          >
            <Text style={[styles.toggleText, mode === MODE_CONTRACT && styles.toggleTextActive]}>
              🛡️  Contrat
            </Text>
          </TouchableOpacity>
          <TouchableOpacity activeOpacity={0.75}
            style={[styles.toggleBtn, mode === MODE_DOCUMENT && styles.toggleBtnActiveDoc]}
            onPress={() => switchMode(MODE_DOCUMENT)}
          >
            <Text style={[styles.toggleText, mode === MODE_DOCUMENT && styles.toggleTextActive]}>
              🔍  Document admin
            </Text>
          </TouchableOpacity>
        </View>

        {/* Historique (Shield uniquement) */}
        {mode === MODE_CONTRACT && showHistory && history.length > 0 && (
          <View style={styles.historyBox}>
            <Text style={styles.historyTitle}>Analyses recentes</Text>
            {history.map(h => (
              <View key={h.id} style={styles.historyItem}>
                <Text style={{ fontSize: 16 }}>{VERDICT_CONFIG[h.verdict]?.icon || '🟠'}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={styles.historyLabel}>{h.type || 'general'} — Score {h.score}/100</Text>
                  <Text style={styles.historyDate}>{new Date(h.date).toLocaleDateString('fr-BE')}</Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Type de contrat (Shield uniquement) */}
        {mode === MODE_CONTRACT && (
          <View style={styles.typesRow}>
            {CONTRACT_TYPES.map(t => (
              <TouchableOpacity activeOpacity={0.75}
                key={t.id || 'auto'}
                style={[styles.typeChip, contractType === t.id && styles.typeChipActive]}
                onPress={() => setContractType(t.id)}
              >
                <Text style={[styles.typeChipText, contractType === t.id && styles.typeChipTextActive]}>
                  {t.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* Input texte */}
        <View style={styles.inputCard}>
          <TextInput
            style={styles.textArea}
            multiline
            numberOfLines={8}
            placeholder={
              mode === MODE_CONTRACT
                ? 'Collez le texte de votre contrat ici (minimum 50 caracteres)...'
                : 'Collez ici le texte d\'une lettre recommandee, d\'un jugement, d\'un avis d\'imposition...'
            }
            placeholderTextColor={colors.textMuted}
            value={text}
            onChangeText={setText}
            textAlignVertical="top"
            accessibilityLabel="Texte du document"
          />
          {mode === MODE_CONTRACT && (
            <Text style={styles.charCount}>
              {text.length} / 50 000 caracteres
            </Text>
          )}
        </View>

        {/* PhotoPicker */}
        <PhotoPicker photos={photos} onPhotosChange={setPhotos} />

        {/* Bouton analyser */}
        <TouchableOpacity activeOpacity={0.75}
          style={[
            styles.analyzeBtn,
            mode === MODE_DOCUMENT && styles.analyzeBtnDoc,
            isDisabled && styles.analyzeBtnDisabled,
          ]}
          onPress={handleAnalyze}
          disabled={isDisabled}
        >
          {loading
            ? <ActivityIndicator color="#FFF" />
            : <Text style={styles.analyzeBtnText}>
                {mode === MODE_CONTRACT ? '🛡️  Analyser le contrat' : '🔍  Decoder ce document'}
              </Text>
          }
        </TouchableOpacity>

        {/* Error */}
        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {/* ════════ RESULTATS SHIELD ════════ */}
        {mode === MODE_CONTRACT && result && verdict && (
          <>
            <View style={[styles.verdictCard, { borderColor: verdict.color }]}>
              <View style={[styles.scoreCircle, { borderColor: verdict.color, backgroundColor: verdict.bg }]}>
                <Text style={[styles.scoreNum, { color: verdict.color }]}>{result.score}</Text>
                <Text style={styles.scoreLbl}>/100</Text>
              </View>
              <Text style={[styles.verdictLabel, { color: verdict.color }]}>
                {verdict.icon} {verdict.label}
              </Text>
              {result.contract_type_detected && (
                <View style={styles.typeBadge}>
                  <Text style={styles.typeBadgeText}>
                    Type detecte : {result.contract_type_detected}
                    {result.region ? ` · ${result.region}` : ''}
                  </Text>
                </View>
              )}
            </View>

            <View style={styles.summaryCard}>
              <Text style={styles.summaryTitle}>Resume</Text>
              <Text style={styles.summaryText}>{result.summary}</Text>
            </View>

            {result.clauses?.length > 0 && (
              <View>
                <Text style={styles.sectionTitle}>
                  Analyse clause par clause ({result.clauses.length})
                </Text>
                {result.clauses.map((clause, i) => {
                  const cv = VERDICT_CONFIG[clause.status] || VERDICT_CONFIG.orange;
                  return (
                    <View key={i} style={[styles.clauseCard, { borderLeftColor: cv.color }]}>
                      <View style={[styles.clauseBadge, { backgroundColor: cv.bg }]}>
                        <Text style={[styles.clauseBadgeText, { color: cv.color }]}>
                          {cv.icon} {clause.status === 'green' ? 'Conforme' : clause.status === 'red' ? 'Clause abusive' : 'Attention'}
                        </Text>
                      </View>
                      <Text style={styles.clauseText}>"{clause.clause_text}"</Text>
                      <Text style={styles.clauseExplain}>{clause.explanation}</Text>
                      {clause.legal_basis && (
                        <View style={styles.legalRef}>
                          <Text style={styles.legalRefText}>📖 {clause.legal_basis}</Text>
                        </View>
                      )}
                    </View>
                  );
                })}
              </View>
            )}

            {result.legal_sources?.length > 0 && (
              <View style={styles.sourcesBox}>
                <Text style={styles.sectionTitle}>Sources juridiques</Text>
                <View style={styles.sourceTags}>
                  {result.legal_sources.map((s, i) => (
                    <View key={i} style={styles.sourceTag}>
                      <Text style={styles.sourceTagText}>{s.source} — {s.title}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {result.disclaimer && (
              <View style={styles.disclaimer}>
                <Text style={styles.disclaimerText}>{result.disclaimer}</Text>
              </View>
            )}
          </>
        )}

        {/* ════════ RESULTATS DECODE ════════ */}
        {mode === MODE_DOCUMENT && result && (
          <View style={styles.decodeResultCard}>
            <View style={[styles.urgencyBanner, { backgroundColor: URGENCY_COLOR[result.urgency ?? 'low'] }]}>
              <Text style={styles.urgencyText}>{URGENCY_LABEL[result.urgency ?? 'low'] ?? result.urgency}</Text>
              {result.deadline && (
                <Text style={styles.urgencyDeadline}>Delai : {result.deadline}</Text>
              )}
            </View>

            {result.document_type && (
              <View style={styles.docTypePill}>
                <Text style={styles.docTypePillText}>
                  📄 {result.document_type.replace(/_/g, ' ')}
                </Text>
              </View>
            )}

            {result.plain_summary && (
              <View style={styles.decodeSection}>
                <Text style={styles.decodeSectionTitle}>En clair</Text>
                <Text style={styles.decodeBodyText}>{result.plain_summary}</Text>
              </View>
            )}

            {result.key_points?.length > 0 && (
              <View style={styles.decodeSection}>
                <Text style={styles.decodeSectionTitle}>Points cles</Text>
                {result.key_points.map((p, i) => (
                  <View key={i} style={styles.listItem}>
                    <Text style={styles.bullet}>•</Text>
                    <Text style={styles.listText}>{p}</Text>
                  </View>
                ))}
              </View>
            )}

            {result.action_required && (
              <View style={styles.actionBox}>
                <Text style={styles.actionTitle}>➡️  Action requise</Text>
                <Text style={styles.actionText}>{result.action_required}</Text>
              </View>
            )}

            {result.legal_context && (
              <View style={styles.legalContextBox}>
                <Text style={styles.legalContextText}>📖 {result.legal_context}</Text>
              </View>
            )}

            {result.disclaimer && (
              <Text style={styles.decodeDisclaimer}>{result.disclaimer}</Text>
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
  content: { padding: 16, paddingBottom: 40 },

  heroHeader: { borderRadius: 16, padding: 20, marginBottom: 12, alignItems: 'center' },
  heroEmoji: { fontSize: 32, marginBottom: 8 },
  heroTitle: { fontSize: 20, fontWeight: '900', color: '#FFF', letterSpacing: 0.5 },
  heroSub: { fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4, textAlign: 'center' },
  historyBtn: { fontSize: 13, color: '#FFF', fontWeight: '600' },

  // Toggle
  toggleRow: {
    flexDirection: 'row', gap: 8, marginBottom: 12,
    backgroundColor: colors.surfaceAlt, borderRadius: 12, padding: 4,
  },
  toggleBtn: {
    flex: 1, paddingVertical: 10, borderRadius: 10, alignItems: 'center',
  },
  toggleBtnActive: { backgroundColor: '#C0392B' },
  toggleBtnActiveDoc: { backgroundColor: '#7B2FBE' },
  toggleText: { fontSize: 13, fontWeight: '600', color: colors.textSecondary },
  toggleTextActive: { color: '#FFF' },

  historyBox: {
    backgroundColor: colors.surface, borderRadius: 12, padding: 14,
    marginBottom: 12, borderWidth: 1, borderColor: colors.border,
  },
  historyTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8 },
  historyItem: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: colors.border },
  historyLabel: { fontSize: 12, fontWeight: '600', color: colors.textPrimary },
  historyDate: { fontSize: 10, color: colors.textMuted },

  typesRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 },
  typeChip: {
    backgroundColor: colors.surface, borderRadius: 20, paddingHorizontal: 14, paddingVertical: 7,
    borderWidth: 1.5, borderColor: colors.border,
  },
  typeChipActive: { backgroundColor: '#C0392B', borderColor: '#C0392B' },
  typeChipText: { fontSize: 11, fontWeight: '600', color: colors.textSecondary },
  typeChipTextActive: { color: '#FFF' },

  inputCard: {
    backgroundColor: colors.surface, borderRadius: 14, padding: 14,
    marginBottom: 12, borderWidth: 1, borderColor: colors.border,
  },
  textArea: {
    fontSize: 14, color: colors.textPrimary, minHeight: 140,
    lineHeight: 20, fontFamily: Platform.OS === 'ios' ? 'System' : 'sans-serif',
  },
  charCount: { fontSize: 10, color: colors.textMuted, textAlign: 'right', marginTop: 4 },

  analyzeBtn: {
    backgroundColor: '#C0392B', borderRadius: 14, paddingVertical: 16,
    alignItems: 'center', marginBottom: 14,
  },
  analyzeBtnDoc: { backgroundColor: '#7B2FBE' },
  analyzeBtnDisabled: { opacity: 0.4 },
  analyzeBtnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },

  errorBox: {
    backgroundColor: '#FEF2F2', borderRadius: 12, padding: 14,
    borderWidth: 1, borderColor: '#FCA5A5', marginBottom: 14,
  },
  errorText: { fontSize: 13, color: colors.error, fontWeight: '600' },

  // Shield result styles
  verdictCard: {
    backgroundColor: colors.surface, borderRadius: 16, padding: 20,
    alignItems: 'center', marginBottom: 14, borderWidth: 2,
    elevation: 3, shadowColor: colors.shadow,
  },
  scoreCircle: {
    width: 100, height: 100, borderRadius: 50, borderWidth: 4,
    alignItems: 'center', justifyContent: 'center', marginBottom: 12,
  },
  scoreNum: { fontSize: 32, fontWeight: '900' },
  scoreLbl: { fontSize: 12, color: colors.textMuted },
  verdictLabel: { fontSize: 16, fontWeight: '800' },
  typeBadge: {
    backgroundColor: colors.surfaceAlt, borderRadius: 8, paddingHorizontal: 10,
    paddingVertical: 4, marginTop: 10,
  },
  typeBadgeText: { fontSize: 11, color: colors.textSecondary, fontWeight: '500' },

  summaryCard: {
    backgroundColor: colors.surface, borderRadius: 14, padding: 14,
    marginBottom: 14, borderWidth: 1, borderColor: colors.border,
  },
  summaryTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 },
  summaryText: { fontSize: 14, color: colors.textPrimary, lineHeight: 21 },

  sectionTitle: { fontSize: 13, fontWeight: '700', color: colors.textPrimary, marginBottom: 10, marginTop: 4 },

  clauseCard: {
    backgroundColor: colors.surface, borderRadius: 12, padding: 14,
    marginBottom: 10, borderLeftWidth: 4, elevation: 1,
    shadowColor: colors.shadow, shadowOffset: { width: 0, height: 1 }, shadowOpacity: 1,
  },
  clauseBadge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3, alignSelf: 'flex-start', marginBottom: 8 },
  clauseBadgeText: { fontSize: 10, fontWeight: '700' },
  clauseText: { fontSize: 13, color: colors.textPrimary, fontStyle: 'italic', lineHeight: 19, marginBottom: 6 },
  clauseExplain: { fontSize: 12, color: colors.textSecondary, lineHeight: 18 },
  legalRef: { backgroundColor: colors.surfaceAlt, borderRadius: 6, padding: 8, marginTop: 8 },
  legalRefText: { fontSize: 11, color: colors.primary, fontWeight: '500' },

  sourcesBox: { marginTop: 4, marginBottom: 14 },
  sourceTags: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  sourceTag: { backgroundColor: colors.surfaceAlt, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 4 },
  sourceTagText: { fontSize: 10, color: colors.primary, fontWeight: '600' },

  disclaimer: {
    backgroundColor: '#F8FAFC', borderRadius: 10, padding: 12,
    borderWidth: 1, borderColor: colors.border, marginBottom: 20,
  },
  disclaimerText: { fontSize: 10, color: colors.textMuted, textAlign: 'center', fontStyle: 'italic', lineHeight: 15 },

  // Decode result styles
  decodeResultCard: {
    backgroundColor: colors.surface, borderRadius: 16, padding: 16,
    marginBottom: 16, elevation: 3, shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 }, shadowOpacity: 1,
  },
  urgencyBanner: {
    borderRadius: 10, padding: 12, flexDirection: 'row',
    alignItems: 'center', justifyContent: 'space-between', marginBottom: 12,
  },
  urgencyText: { color: '#FFF', fontSize: 14, fontWeight: '700' },
  urgencyDeadline: { color: 'rgba(255,255,255,0.9)', fontSize: 12, fontWeight: '600' },

  docTypePill: {
    alignSelf: 'flex-start', backgroundColor: colors.surfaceAlt,
    borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4, marginBottom: 12,
  },
  docTypePillText: { fontSize: 11, color: colors.textSecondary, fontWeight: '600' },

  decodeSection: { marginBottom: 14 },
  decodeSectionTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  decodeBodyText: { fontSize: 14, color: colors.textPrimary, lineHeight: 21 },

  listItem: { flexDirection: 'row', gap: 8, marginBottom: 6 },
  bullet: { color: colors.primary, fontWeight: '700', fontSize: 14 },
  listText: { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 19 },

  actionBox: {
    backgroundColor: '#EFF6FF', borderRadius: 10, padding: 12,
    borderWidth: 1, borderColor: '#BFDBFE', marginBottom: 12,
  },
  actionTitle: { fontSize: 13, fontWeight: '700', color: colors.primary, marginBottom: 4 },
  actionText: { fontSize: 13, color: colors.textPrimary, lineHeight: 19 },

  legalContextBox: {
    backgroundColor: colors.surfaceAlt, borderRadius: 8, padding: 10, marginBottom: 12,
  },
  legalContextText: { fontSize: 11, color: colors.textSecondary, lineHeight: 16 },

  decodeDisclaimer: {
    fontSize: 10, color: colors.textMuted, fontStyle: 'italic',
    textAlign: 'center', lineHeight: 14,
  },
});
