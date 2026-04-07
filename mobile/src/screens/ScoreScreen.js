import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator,
} from 'react-native';
import { getScoreQuestions, evaluateScore } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import { LinearGradient } from 'expo-linear-gradient';

const SCORE_YELLOW = '#F39C12';
const ANSWER_OPTIONS = [
  { id: 'oui',     label: '✓ Oui',     color: '#27AE60', bg: '#F0FDF4' },
  { id: 'partiel', label: '⚡ Partiel', color: '#F39C12', bg: '#FFFBEB' },
  { id: 'non',     label: '✗ Non',     color: '#E74C3C', bg: '#FEF2F2' },
  { id: 'na',      label: '— N/A',     color: colors.textMuted, bg: colors.surfaceAlt },
];
const RATING_COLOR = { excellent: '#27AE60', bon: '#2980B9', moyen: '#F39C12', critique: '#E74C3C' };

export default function ScoreScreen() {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers]     = useState({});
  const [fetching, setFetching]   = useState(true);
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState(null);
  const [error, setError]         = useState(null);
  const [photos, setPhotos] = useState([]);

  useEffect(() => {
    getScoreQuestions()
      .then((d) => setQuestions(d.questions ?? []))
      .catch(() => setQuestions([]))
      .finally(() => setFetching(false));
  }, []);

  const setAnswer = (qId, val) => setAnswers((a) => ({ ...a, [qId]: val }));

  const evaluate = async () => {
    setLoading(true); setResult(null); setError(null);
    try {
      const data = await evaluateScore(answers);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally {
      setLoading(false);
    }
  };

  const answeredCount = Object.keys(answers).length;
  const canSubmit = answeredCount >= (questions.length * 0.7);

  if (fetching) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={SCORE_YELLOW} size="large" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

      {/* Header */}
      <LinearGradient colors={['#7C4D00', '#F39C12']} style={styles.heroHeader}>
        <Text style={styles.heroEmoji}>📊</Text>
        <Text style={styles.heroTitle}>Score juridique</Text>
        <Text style={styles.heroSub}>
          {answeredCount}/{questions.length} réponses · Santé juridique sur 100
        </Text>
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${(answeredCount / Math.max(questions.length, 1)) * 100}%` }]} />
        </View>
      </LinearGradient>

      {/* Questions */}
      <View style={styles.card}>
        {questions.map((q, i) => (
          <View key={q.id ?? i} style={[styles.questionItem, i > 0 && styles.questionBorder]}>
            <View style={styles.questionRow}>
              <View style={styles.qNumCircle}>
                <Text style={styles.qNum}>{i + 1}</Text>
              </View>
              <Text style={styles.questionText}>{q.question}</Text>
              {q.weight && (
                <View style={styles.weightPill}>
                  <Text style={styles.weightText}>{q.weight}pts</Text>
                </View>
              )}
            </View>
            <View style={styles.answerRow}>
              {ANSWER_OPTIONS.map((opt) => (
                <TouchableOpacity activeOpacity={0.75}
                  key={opt.id}
                  style={[
                    styles.answerBtn,
                    { backgroundColor: answers[q.id ?? i] === opt.id ? opt.bg : colors.background },
                    answers[q.id ?? i] === opt.id && { borderColor: opt.color },
                  ]}
                  onPress={() => setAnswer(q.id ?? i, opt.id)}
                >
                  <Text style={[
                    styles.answerBtnText,
                    { color: answers[q.id ?? i] === opt.id ? opt.color : colors.textMuted },
                    answers[q.id ?? i] === opt.id && { fontWeight: '700' },
                  ]}>
                    {opt.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        ))}
      </View>

      <PhotoPicker photos={photos} onPhotosChange={setPhotos} />

            <TouchableOpacity activeOpacity={0.75}
        style={[styles.btn, (!canSubmit || loading) && styles.btnDisabled]}
        onPress={evaluate}
        disabled={!canSubmit || loading}
      >
        {loading
          ? <ActivityIndicator color="#FFF" />
          : <Text style={styles.btnText}>📊  Calculer mon score</Text>
        }
      </TouchableOpacity>
      {!canSubmit && (
        <Text style={styles.hintText}>Répondez à au moins 70% des questions</Text>
      )}

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>⚠️ {error}</Text>
        </View>
      )}

      {result && (
        <View style={styles.card}>
          {/* Score gauge */}
          <View style={[styles.scoreBanner, { backgroundColor: RATING_COLOR[result.rating] ?? SCORE_YELLOW }]}>
            <Text style={styles.scorePct}>{result.percentage?.toFixed(0) ?? result.score}%</Text>
            <Text style={styles.scoreLabel}>{result.rating?.toUpperCase() ?? 'SCORE'}</Text>
            <Text style={styles.scoreDetail}>{result.score} / {result.total_possible} points</Text>
          </View>

          {/* Weak points */}
          {result.weak_points?.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Points à améliorer</Text>
              {result.weak_points.map((w, i) => (
                <View key={i} style={styles.weakItem}>
                  <Text style={styles.weakQ}>⚠️ {w.question}</Text>
                  {w.recommendation && (
                    <Text style={styles.weakReco}>→ {w.recommendation}</Text>
                  )}
                  {w.legal_basis && (
                    <Text style={styles.weakLegal}>📖 {w.legal_basis}</Text>
                  )}
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
            ⚖️ Lexavo est un outil d'information juridique. Il ne remplace pas un avocat ni un conseiller juridique professionnel.
          </Text>
        </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content:   { padding: 16, paddingBottom: 40 },
  center:    { flex: 1, alignItems: 'center', justifyContent: 'center' },

  heroHeader: { borderRadius: 16, padding: 20, marginBottom: 16, alignItems: 'center' },
  heroEmoji: { fontSize: 32, marginBottom: 8 },
  heroTitle: { fontSize: 20, fontWeight: '900', color: '#FFF', letterSpacing: 0.5 },
  heroSub: { fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4, textAlign: 'center', marginBottom: 8 },
  progressBar: { height: 4, backgroundColor: 'rgba(255,255,255,0.3)', borderRadius: 2, width: '100%' },
  progressFill: { height: 4, backgroundColor: '#FFF', borderRadius: 2 },

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

  questionItem: { paddingVertical: 12 },
  questionBorder: { borderTopWidth: 1, borderTopColor: colors.border },
  questionRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 8 },
  qNumCircle: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  qNum: { color: '#FFF', fontSize: 11, fontWeight: '700' },
  questionText: { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 19 },
  weightPill: {
    backgroundColor: '#FFF7E0',
    borderRadius: 8,
    paddingHorizontal: 6,
    paddingVertical: 2,
    flexShrink: 0,
  },
  weightText: { fontSize: 9, color: '#D97706', fontWeight: '700' },

  answerRow: { flexDirection: 'row', gap: 6, marginLeft: 30 },
  answerBtn: {
    flex: 1,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: 6,
    alignItems: 'center',
  },
  answerBtnText: { fontSize: 11 },

  btn: {
    backgroundColor: SCORE_YELLOW,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 8,
  },
  btnDisabled: { opacity: 0.45 },
  btnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },
  hintText: { fontSize: 11, color: colors.textMuted, textAlign: 'center', marginBottom: 12 },

  errorBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#FCA5A5',
    marginBottom: 16,
  },
  errorText: { fontSize: 13, color: colors.error, fontWeight: '600' },

  scoreBanner: {
    borderRadius: 10,
    padding: 16,
    alignItems: 'center',
    marginBottom: 14,
  },
  scorePct:    { color: '#FFF', fontSize: 42, fontWeight: '900' },
  scoreLabel:  { color: 'rgba(255,255,255,0.85)', fontSize: 16, fontWeight: '700', letterSpacing: 2, marginTop: 2 },
  scoreDetail: { color: 'rgba(255,255,255,0.7)', fontSize: 11, marginTop: 4 },

  section:      { marginBottom: 14 },
  sectionTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },

  weakItem: {
    backgroundColor: '#FEF2F2',
    borderRadius: 8,
    padding: 10,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: '#FCA5A5',
  },
  weakQ:     { fontSize: 12, fontWeight: '600', color: colors.textPrimary, marginBottom: 3 },
  weakReco:  { fontSize: 12, color: '#7F1D1D', lineHeight: 17, marginBottom: 2 },
  weakLegal: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic' },

  disclaimer: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic', textAlign: 'center' },
});
