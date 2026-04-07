import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform, TextInput,
} from 'react-native';
import { getAuditQuestions, generateAudit } from '../api/client';
import { colors } from '../theme/colors';

const VERDICT_COLOR = { green: '#27AE60', orange: '#F39C12', red: '#E74C3C' };
const VERDICT_LABEL = {
  green:  'Conforme',
  orange: 'Conformite partielle',
  red:    'Non conforme',
};
const ANSWER_OPTIONS = [
  { key: 'yes',     label: 'Oui',     color: '#27AE60' },
  { key: 'no',      label: 'Non',     color: '#E74C3C' },
  { key: 'partial', label: 'Partiel', color: '#F39C12' },
  { key: 'na',      label: 'N/A',     color: '#9CA3AF' },
];
const COMPANY_TYPES = [
  { key: 'srl',               label: 'SRL' },
  { key: 'sa',                label: 'SA' },
  { key: 'sc',                label: 'SC' },
  { key: 'independant',       label: 'Independant' },
  { key: 'asbl',              label: 'ASBL' },
  { key: 'pme',               label: 'PME' },
  { key: 'grande_entreprise', label: 'Grande entreprise' },
];

export default function AuditScreen() {
  const [step, setStep]               = useState('form');   // form | questions | result
  const [companyType, setCompanyType] = useState('srl');
  const [companyName, setCompanyName] = useState('');
  const [questions, setQuestions]     = useState([]);
  const [answers, setAnswers]         = useState({});
  const [loading, setLoading]         = useState(false);
  const [result, setResult]           = useState(null);
  const [error, setError]             = useState(null);

  // ── Load questions ──────────────────────────────────────────────────────
  const loadQuestions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAuditQuestions(companyType);
      const q = data.questions ?? data ?? [];
      setQuestions(q);
      // Init answers
      const init = {};
      q.forEach((cat) => {
        (cat.questions ?? []).forEach((item) => {
          init[item.id] = null;
        });
      });
      setAnswers(init);
      setStep('questions');
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur chargement questions');
    } finally {
      setLoading(false);
    }
  };

  // ── Submit audit ────────────────────────────────────────────────────────
  const submitAudit = async () => {
    setLoading(true);
    setError(null);
    try {
      const formattedAnswers = Object.entries(answers)
        .filter(([, v]) => v !== null)
        .map(([qid, answer]) => ({ question_id: parseInt(qid, 10), answer }));

      const body = {
        answers: formattedAnswers,
        company_type: companyType,
        company_name: companyName || undefined,
      };
      const data = await generateAudit(body);
      setResult(data);
      setStep('result');
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur generation audit');
    } finally {
      setLoading(false);
    }
  };

  // ── Answer count ────────────────────────────────────────────────────────
  const totalQuestions = Object.keys(answers).length;
  const answeredCount  = Object.values(answers).filter((v) => v !== null).length;

  // ── Render: Company form ────────────────────────────────────────────────
  if (step === 'form') {
    return (
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={90}
      >
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <View style={styles.card}>
            <View style={styles.featureHeader}>
              <Text style={styles.featureEmoji}>📋</Text>
              <View>
                <Text style={styles.featureTitle}>Audit de conformite</Text>
                <Text style={styles.featureSub}>30 questions, 8 domaines du droit belge</Text>
              </View>
            </View>

            {/* Company name */}
            <Text style={styles.label}>Nom de l'entreprise (optionnel)</Text>
            <TextInput
              style={styles.input}
              placeholder="Ex: Ma Societe SRL"
              placeholderTextColor={colors.textMuted}
              value={companyName}
              onChangeText={setCompanyName}
            />

            {/* Company type */}
            <Text style={styles.label}>Type d'entreprise</Text>
            <View style={styles.chipRow}>
              {COMPANY_TYPES.map((ct) => (
                <TouchableOpacity activeOpacity={0.75}
                  key={ct.key}
                  style={[styles.chip, companyType === ct.key && styles.chipActive]}
                  onPress={() => setCompanyType(ct.key)}
                >
                  <Text style={[styles.chipText, companyType === ct.key && styles.chipTextActive]}>
                    {ct.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <TouchableOpacity activeOpacity={0.75}
              style={[styles.btn, loading && styles.btnDisabled]}
              onPress={loadQuestions}
              disabled={loading}
            >
              {loading
                ? <ActivityIndicator color="#FFF" />
                : <Text style={styles.btnText}>Demarrer l'audit</Text>
              }
            </TouchableOpacity>
          </View>

          {error && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    );
  }

  // ── Render: Questions ──────────────────────────────────────────────────
  if (step === 'questions') {
    return (
      <View style={styles.container}>
        <ScrollView contentContainerStyle={styles.content}>
          {/* Progress */}
          <View style={styles.progressCard}>
            <Text style={styles.progressText}>
              {answeredCount} / {totalQuestions} questions
            </Text>
            <View style={styles.progressBar}>
              <View style={[styles.progressFill, { width: `${totalQuestions > 0 ? (answeredCount / totalQuestions) * 100 : 0}%` }]} />
            </View>
          </View>

          {/* Categories */}
          {questions.map((cat, ci) => (
            <View key={ci} style={styles.card}>
              <Text style={styles.categoryTitle}>{cat.category ?? cat.name ?? `Categorie ${ci + 1}`}</Text>
              {(cat.questions ?? []).map((q) => (
                <View key={q.id} style={styles.questionBlock}>
                  <Text style={styles.questionText}>{q.text ?? q.question}</Text>
                  <View style={styles.answerRow}>
                    {ANSWER_OPTIONS.map((opt) => (
                      <TouchableOpacity activeOpacity={0.75}
                        key={opt.key}
                        style={[
                          styles.answerBtn,
                          answers[q.id] === opt.key && { backgroundColor: opt.color },
                        ]}
                        onPress={() => setAnswers((prev) => ({ ...prev, [q.id]: opt.key }))}
                      >
                        <Text
                          style={[
                            styles.answerBtnText,
                            answers[q.id] === opt.key && { color: '#FFF' },
                          ]}
                        >
                          {opt.label}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              ))}
            </View>
          ))}

          {error && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {/* Submit */}
          <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, (loading || answeredCount === 0) && styles.btnDisabled]}
            onPress={submitAudit}
            disabled={loading || answeredCount === 0}
          >
            {loading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>Lancer l'audit</Text>
            }
          </TouchableOpacity>

          {/* Back */}
          <TouchableOpacity activeOpacity={0.75} style={styles.linkBtn} onPress={() => setStep('form')}>
            <Text style={styles.linkBtnText}>Retour</Text>
          </TouchableOpacity>
        </ScrollView>
      </View>
    );
  }

  // ── Render: Result ─────────────────────────────────────────────────────
  if (step === 'result' && result) {
    const verdictColor = VERDICT_COLOR[result.verdict] ?? VERDICT_COLOR.orange;
    const verdictLabel = result.verdict_label ?? VERDICT_LABEL[result.verdict] ?? result.verdict;

    return (
      <View style={styles.container}>
        <ScrollView contentContainerStyle={styles.content}>
          {/* Score circle */}
          <View style={styles.card}>
            <View style={styles.scoreContainer}>
              <View style={[styles.scoreCircle, { borderColor: verdictColor }]}>
                <Text style={[styles.scoreValue, { color: verdictColor }]}>{result.score ?? 0}</Text>
                <Text style={styles.scoreMax}>/100</Text>
              </View>
              <View style={[styles.verdictBanner, { backgroundColor: verdictColor }]}>
                <Text style={styles.verdictText}>{verdictLabel}</Text>
              </View>
            </View>
          </View>

          {/* Critical risks */}
          {result.critical_risks?.length > 0 && (
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Risques critiques</Text>
              {result.critical_risks.map((risk, i) => (
                <View key={i} style={styles.riskItem}>
                  <Text style={styles.riskDot}>!!</Text>
                  <Text style={styles.riskText}>{typeof risk === 'string' ? risk : risk.description ?? risk.text}</Text>
                </View>
              ))}
            </View>
          )}

          {/* Category results */}
          {result.category_results && (
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Resultats par domaine</Text>
              {Object.entries(result.category_results).map(([cat, data]) => (
                <View key={cat} style={styles.catRow}>
                  <View style={[styles.catDot, { backgroundColor: VERDICT_COLOR[data.verdict] ?? '#9CA3AF' }]} />
                  <Text style={styles.catName}>{cat}</Text>
                  <Text style={[styles.catScore, { color: VERDICT_COLOR[data.verdict] ?? '#9CA3AF' }]}>
                    {data.score}/100
                  </Text>
                </View>
              ))}
            </View>
          )}

          {/* Recommendations */}
          {result.recommendations?.length > 0 && (
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Recommandations</Text>
              {result.recommendations.map((rec, i) => (
                <View key={i} style={styles.recCard}>
                  <View style={styles.recHeader}>
                    {rec.priority === 'high' && <Text style={styles.recPriorityHigh}>HAUTE</Text>}
                    {rec.priority === 'medium' && <Text style={styles.recPriorityMedium}>MOYENNE</Text>}
                    {rec.priority === 'low' && <Text style={styles.recPriorityLow}>BASSE</Text>}
                    {rec.deadline && <Text style={styles.recDeadline}>{rec.deadline}</Text>}
                  </View>
                  <Text style={styles.recAction}>{rec.action}</Text>
                  {rec.legal_ref && (
                    <Text style={styles.recLegal}>{rec.legal_ref}</Text>
                  )}
                </View>
              ))}
            </View>
          )}

          {/* Disclaimer */}
          <Text style={styles.disclaimer}>
            Cet audit est un outil d'orientation. Il ne remplace pas un conseil juridique professionnel.
          </Text>

          <View style={{ marginTop: 12, padding: 10, backgroundColor: '#FFFBEB', borderRadius: 8, borderWidth: 1, borderColor: '#FDE68A' }}>
            <Text style={{ fontSize: 10, color: '#92400E', textAlign: 'center', fontStyle: 'italic', lineHeight: 14 }}>
              {'\u2696\ufe0f Lexavo est un outil d\'information juridique. Il ne remplace pas un avocat ni un conseiller juridique professionnel.'}
            </Text>
          </View>

          {/* Restart */}
          <TouchableOpacity activeOpacity={0.75} style={styles.linkBtn} onPress={() => { setStep('form'); setResult(null); }}>
            <Text style={styles.linkBtnText}>Nouvel audit</Text>
          </TouchableOpacity>
        </ScrollView>
      </View>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content:   { padding: 16, paddingBottom: 40 },

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

  label: { fontSize: 13, fontWeight: '600', color: colors.textSecondary, marginBottom: 6, marginTop: 10 },
  input: {
    backgroundColor: colors.background,
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 8,
  },

  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 },
  chip: {
    paddingHorizontal: 12, paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.border,
  },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText:       { fontSize: 12, color: colors.textSecondary, fontWeight: '600' },
  chipTextActive: { color: '#FFF' },

  btn: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 8,
  },
  btnDisabled: { opacity: 0.45 },
  btnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },

  linkBtn:     { alignItems: 'center', paddingVertical: 12 },
  linkBtnText: { color: colors.primary, fontSize: 14, fontWeight: '600' },

  errorBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#FCA5A5',
    marginBottom: 16,
  },
  errorText: { fontSize: 13, color: colors.error, fontWeight: '600' },

  // Progress
  progressCard: { backgroundColor: colors.surface, borderRadius: 12, padding: 14, marginBottom: 16 },
  progressText: { fontSize: 13, fontWeight: '600', color: colors.textSecondary, marginBottom: 8, textAlign: 'center' },
  progressBar:  { height: 6, backgroundColor: colors.surfaceAlt, borderRadius: 3, overflow: 'hidden' },
  progressFill: { height: 6, backgroundColor: colors.primary, borderRadius: 3 },

  // Questions
  categoryTitle: { fontSize: 14, fontWeight: '700', color: colors.primary, marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.5 },
  questionBlock: { marginBottom: 14 },
  questionText:  { fontSize: 13, color: colors.textPrimary, lineHeight: 19, marginBottom: 8 },
  answerRow:     { flexDirection: 'row', gap: 6 },
  answerBtn: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: colors.surfaceAlt,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  answerBtnText: { fontSize: 11, fontWeight: '700', color: colors.textSecondary },

  // Score
  scoreContainer: { alignItems: 'center', paddingVertical: 10 },
  scoreCircle: {
    width: 120, height: 120,
    borderRadius: 60,
    borderWidth: 6,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 14,
  },
  scoreValue: { fontSize: 36, fontWeight: '800' },
  scoreMax:   { fontSize: 14, color: colors.textMuted, marginTop: -4 },
  verdictBanner: { borderRadius: 20, paddingHorizontal: 20, paddingVertical: 8 },
  verdictText:   { color: '#FFF', fontSize: 14, fontWeight: '700' },

  // Sections
  sectionTitle: {
    fontSize: 13, fontWeight: '700', color: colors.textSecondary,
    marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5,
  },

  // Risks
  riskItem: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 8 },
  riskDot:  { fontSize: 12, color: '#E74C3C', fontWeight: '800', marginTop: 1 },
  riskText: { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 19 },

  // Category results
  catRow:   { flexDirection: 'row', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.border },
  catDot:   { width: 10, height: 10, borderRadius: 5, marginRight: 10 },
  catName:  { flex: 1, fontSize: 13, fontWeight: '600', color: colors.textPrimary, textTransform: 'capitalize' },
  catScore: { fontSize: 13, fontWeight: '700' },

  // Recommendations
  recCard: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
  },
  recHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  recPriorityHigh:   { fontSize: 10, fontWeight: '800', color: '#E74C3C', backgroundColor: '#FEE2E2', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, overflow: 'hidden' },
  recPriorityMedium: { fontSize: 10, fontWeight: '800', color: '#F39C12', backgroundColor: '#FEF3C7', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, overflow: 'hidden' },
  recPriorityLow:    { fontSize: 10, fontWeight: '800', color: '#27AE60', backgroundColor: '#D1FAE5', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, overflow: 'hidden' },
  recDeadline: { fontSize: 10, color: colors.textMuted, fontWeight: '600' },
  recAction:   { fontSize: 13, color: colors.textPrimary, lineHeight: 19, marginBottom: 4 },
  recLegal:    { fontSize: 11, color: colors.textMuted, fontStyle: 'italic' },

  disclaimer: {
    fontSize: 10,
    color: colors.textMuted,
    fontStyle: 'italic',
    textAlign: 'center',
    lineHeight: 14,
    marginTop: 4,
    marginBottom: 8,
  },
});
