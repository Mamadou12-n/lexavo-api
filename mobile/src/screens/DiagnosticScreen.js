/**
 * DiagnosticScreen — Lexavo
 * 3 modes : Diagnostic IA | Score rapide | Succession
 */

import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { runDiagnostic, getScoreQuestions, evaluateScore, getHeritageGuide } from '../api/client';
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

const ANSWER_OPTIONS = [
  { id: 'oui',     label: '✓ Oui',     color: '#27AE60', bg: '#F0FDF4' },
  { id: 'partiel', label: '⚡ Partiel', color: '#F39C12', bg: '#FFFBEB' },
  { id: 'non',     label: '✗ Non',     color: '#E74C3C', bg: '#FEF2F2' },
  { id: 'na',      label: '— N/A',     color: colors.textMuted, bg: colors.surfaceAlt },
];

const REGIONS_H = [
  { id: 'bruxelles', label: '🏙️ Bruxelles' },
  { id: 'wallonie',  label: '🌿 Wallonie' },
  { id: 'flandre',   label: '🦁 Flandre' },
];

const HEIR_TYPES = [
  { id: 'enfant',      label: 'Enfant' },
  { id: 'conjoint',    label: 'Conjoint' },
  { id: 'parent',      label: 'Parent' },
  { id: 'frere_soeur', label: 'Frère/Sœur' },
  { id: 'autre',       label: 'Autre' },
];

export default function DiagnosticScreen() {
  const [mode, setMode] = useState('diagnostic'); // 'diagnostic' | 'score' | 'succession'

  // ── Diagnostic ──
  const [problem, setProblem]   = useState('');
  const [userType, setUserType] = useState('particulier');
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState(null);
  const [photos, setPhotos]     = useState([]);

  // ── Score rapide ──
  const [questions, setQuestions]   = useState([]);
  const [answers, setAnswers]       = useState({});
  const [fetching, setFetching]     = useState(false);
  const [scoreResult, setScoreResult] = useState(null);
  const [scoreLoading, setScoreLoading] = useState(false);
  const [scoreError, setScoreError] = useState(null);

  // ── Succession ──
  const [hRegion, setHRegion]       = useState('bruxelles');
  const [estateValue, setEstate]    = useState('');
  const [heirType, setHeirType]     = useState('enfant');
  const [numHeirs, setNumHeirs]     = useState('1');
  const [hResult, setHResult]       = useState(null);
  const [hLoading, setHLoading]     = useState(false);
  const [hError, setHError]         = useState(null);

  // Charger les questions score à l'affichage du mode
  useEffect(() => {
    if (mode !== 'score' || questions.length > 0) return;
    setFetching(true);
    getScoreQuestions()
      .then((d) => setQuestions(d.questions ?? []))
      .catch(() => setQuestions([]))
      .finally(() => setFetching(false));
  }, [mode]);

  const switchMode = (m) => {
    setMode(m);
    setResult(null); setError(null); setProblem('');
    setScoreResult(null); setScoreError(null); setAnswers({});
    setHResult(null); setHError(null);
  };

  // ── Diagnostic ──
  const analyzeDiag = async () => {
    if (!problem.trim()) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const data = await runDiagnostic(problem.trim(), userType);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally { setLoading(false); }
  };

  // ── Score rapide ──
  const setAnswer = (qId, val) => setAnswers((a) => ({ ...a, [qId]: val }));
  const answeredCount = Object.keys(answers).length;
  const canSubmit = answeredCount >= Math.max(1, Math.floor((questions.length || 1) * 0.7));

  const evaluateSc = async () => {
    setScoreLoading(true); setScoreResult(null); setScoreError(null);
    try {
      const data = await evaluateScore(answers);
      setScoreResult(data);
    } catch (e) {
      setScoreError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally { setScoreLoading(false); }
  };

  // ── Succession ──
  const generateHeritage = async () => {
    if (!estateValue) { setHError('Entre la valeur de la succession.'); return; }
    setHLoading(true); setHResult(null); setHError(null);
    try {
      const heirs = Array.from({ length: parseInt(numHeirs) || 1 }, (_, i) => ({
        id: i + 1, type: heirType, name: `Héritier ${i + 1}`,
      }));
      const data = await getHeritageGuide(hRegion, parseFloat(estateValue), heirs);
      setHResult(data);
    } catch (e) {
      setHError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally { setHLoading(false); }
  };

  // ── Toggle header ──────────────────────────────────────────────────────────
  const ModeToggle = () => (
    <View style={s.toggle}>
      {[
        { id: 'diagnostic', label: '🔬 Diagnostic' },
        { id: 'score',      label: '📊 Score' },
        { id: 'succession', label: '🏛️ Succession' },
      ].map((m) => (
        <TouchableOpacity key={m.id} style={[s.toggleBtn, mode === m.id && s.toggleBtnActive]} onPress={() => switchMode(m.id)}>
          <Text style={[s.toggleText, mode === m.id && s.toggleTextActive]}>{m.label}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );

  // ════════════════════════════════════════════════════════════════════════════
  //  RENDER
  // ════════════════════════════════════════════════════════════════════════════

  return (
    <KeyboardAvoidingView style={s.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
      <ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">

        {/* ── Header ── */}
        <LinearGradient
          colors={mode === 'score' ? ['#7C4D00', '#F39C12'] : mode === 'succession' ? ['#3D1F00', '#8B4513'] : ['#7C2D12', '#C45A2D']}
          style={s.heroHeader}
        >
          <Text style={s.heroEmoji}>{mode === 'score' ? '📊' : mode === 'succession' ? '🏛️' : '🔬'}</Text>
          <Text style={s.heroTitle}>{mode === 'score' ? 'Score juridique' : mode === 'succession' ? 'Guide successoral' : 'Diagnostic juridique'}</Text>
          <Text style={s.heroSub}>{mode === 'score' ? 'Santé juridique sur 100' : mode === 'succession' ? 'Droits de succession belges' : 'Analyse multi-branches du droit belge'}</Text>
        </LinearGradient>

        <ModeToggle />

        {/* ════════════════════════════════════════════════════════════════════
            MODE DIAGNOSTIC
            ════════════════════════════════════════════════════════════════════ */}
        {mode === 'diagnostic' && (
          <>
            <View style={s.card}>
              <Text style={s.fieldLabel}>Votre profil</Text>
              <View style={s.typeRow}>
                {USER_TYPES.map((t) => (
                  <TouchableOpacity activeOpacity={0.75} key={t.id}
                    style={[s.typeBtn, userType === t.id && s.typeBtnActive]}
                    onPress={() => setUserType(t.id)}
                  >
                    <Text style={[s.typeLabel, userType === t.id && s.typeLabelActive]}>{t.label}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={[s.fieldLabel, { marginTop: 12 }]}>Décrivez votre problème juridique</Text>
              <TextInput
                style={s.textArea} multiline numberOfLines={6}
                placeholder="Décrivez votre situation en détail..."
                placeholderTextColor={colors.textMuted}
                value={problem} onChangeText={setProblem}
                textAlignVertical="top"
              />
              <PhotoPicker photos={photos} onPhotosChange={setPhotos} />
              <TouchableOpacity activeOpacity={0.75}
                style={[s.btn, (!problem.trim() || loading) && s.btnDisabled]}
                onPress={analyzeDiag} disabled={!problem.trim() || loading}
              >
                {loading ? <ActivityIndicator color="#FFF" /> : <Text style={s.btnText}>🔬  Lancer le diagnostic</Text>}
              </TouchableOpacity>
            </View>

            {error && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {error}</Text></View>}

            {result && (
              <View style={s.card}>
                <ModelBadge model={result.model} />
                {result.branches?.length > 0 && (
                  <View style={s.section}>
                    <Text style={s.sectionTitle}>Branches du droit concernées</Text>
                    <View style={s.branchRow}>
                      {result.branches.map((b, i) => (
                        <View key={i} style={s.branchPill}><Text style={s.branchText}>{b}</Text></View>
                      ))}
                    </View>
                  </View>
                )}
                {result.situation_summary && (
                  <View style={s.section}>
                    <Text style={s.sectionTitle}>Analyse de la situation</Text>
                    <Text style={s.bodyText}>{result.situation_summary}</Text>
                  </View>
                )}
                {result.applicable_law?.length > 0 && (
                  <View style={s.section}>
                    <Text style={s.sectionTitle}>Droit applicable</Text>
                    {result.applicable_law.map((l, i) => (
                      <View key={i} style={s.listItem}>
                        <Text style={s.bullet}>⚖️</Text>
                        <Text style={s.listText}>{l}</Text>
                      </View>
                    ))}
                  </View>
                )}
                {result.recommended_steps?.length > 0 && (
                  <View style={s.section}>
                    <Text style={s.sectionTitle}>Étapes recommandées</Text>
                    {result.recommended_steps.map((st, i) => (
                      <View key={i} style={s.stepItem}>
                        <View style={s.stepNumCircle}><Text style={s.stepNum}>{i + 1}</Text></View>
                        <Text style={s.stepText}>{typeof st === 'string' ? st : st.description}</Text>
                      </View>
                    ))}
                  </View>
                )}
                {result.urgency_level && (
                  <View style={[s.urgencyBox, { borderColor: result.urgency_level === 'high' ? colors.error : colors.warning }]}>
                    <Text style={s.urgencyText}>
                      {result.urgency_level === 'high' ? '🚨' : '⚠️'} Urgence : {result.urgency_level}
                    </Text>
                  </View>
                )}
                {result.disclaimer && <Text style={s.disclaimer}>{result.disclaimer}</Text>}
              </View>
            )}
          </>
        )}

        {/* ════════════════════════════════════════════════════════════════════
            MODE SCORE RAPIDE
            ════════════════════════════════════════════════════════════════════ */}
        {mode === 'score' && (
          <>
            {fetching && <ActivityIndicator color={DIAG_ORANGE} size="large" style={{ margin: 32 }} />}
            {!fetching && questions.length === 0 && (
              <View style={s.errorBox}><Text style={s.errorText}>Impossible de charger les questions.</Text></View>
            )}
            {!fetching && questions.length > 0 && !scoreResult && (
              <>
                <View style={s.card}>
                  <Text style={[s.fieldLabel, { marginBottom: 4 }]}>
                    {answeredCount}/{questions.length} réponses complétées
                  </Text>
                  <View style={s.progressBar}>
                    <View style={[s.progressFill, { width: `${(answeredCount / questions.length) * 100}%` }]} />
                  </View>
                </View>
                <View style={s.card}>
                  {questions.map((q, i) => (
                    <View key={q.id ?? i} style={[s.questionItem, i > 0 && s.questionBorder]}>
                      <View style={s.questionRow}>
                        <View style={s.qNumCircle}><Text style={s.qNum}>{i + 1}</Text></View>
                        <Text style={s.questionText}>{q.question}</Text>
                      </View>
                      <View style={s.answerRow}>
                        {ANSWER_OPTIONS.map((opt) => (
                          <TouchableOpacity activeOpacity={0.75} key={opt.id}
                            style={[s.answerBtn, { backgroundColor: answers[q.id ?? i] === opt.id ? opt.bg : colors.background }, answers[q.id ?? i] === opt.id && { borderColor: opt.color }]}
                            onPress={() => setAnswer(q.id ?? i, opt.id)}
                          >
                            <Text style={[s.answerBtnText, { color: answers[q.id ?? i] === opt.id ? opt.color : colors.textMuted }, answers[q.id ?? i] === opt.id && { fontWeight: '700' }]}>
                              {opt.label}
                            </Text>
                          </TouchableOpacity>
                        ))}
                      </View>
                    </View>
                  ))}
                </View>
                {scoreError && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {scoreError}</Text></View>}
                <TouchableOpacity activeOpacity={0.75}
                  style={[s.btn, (!canSubmit || scoreLoading) && s.btnDisabled]}
                  onPress={evaluateSc} disabled={!canSubmit || scoreLoading}
                >
                  {scoreLoading ? <ActivityIndicator color="#FFF" /> : <Text style={s.btnText}>📊  Calculer mon score</Text>}
                </TouchableOpacity>
              </>
            )}
            {scoreResult && (
              <View style={s.card}>
                <Text style={[s.fieldLabel, { textAlign: 'center' }]}>SCORE JURIDIQUE</Text>
                <Text style={[s.scoreNum, { color: scoreResult.score >= 70 ? '#27AE60' : scoreResult.score >= 40 ? '#F39C12' : '#E74C3C' }]}>
                  {scoreResult.score}/100
                </Text>
                {scoreResult.rating && <Text style={[s.sectionTitle, { textAlign: 'center' }]}>{scoreResult.rating}</Text>}
                {scoreResult.summary && <Text style={[s.bodyText, { marginTop: 12 }]}>{scoreResult.summary}</Text>}
                {scoreResult.recommendations?.length > 0 && (
                  <View style={[s.section, { marginTop: 14 }]}>
                    <Text style={s.sectionTitle}>Recommandations</Text>
                    {scoreResult.recommendations.map((r, i) => (
                      <View key={i} style={s.listItem}>
                        <Text style={s.bullet}>→</Text>
                        <Text style={s.listText}>{typeof r === 'string' ? r : r.action || JSON.stringify(r)}</Text>
                      </View>
                    ))}
                  </View>
                )}
                <TouchableOpacity style={[s.btn, { marginTop: 16 }]} onPress={() => { setScoreResult(null); setAnswers({}); }}>
                  <Text style={s.btnText}>Recommencer</Text>
                </TouchableOpacity>
              </View>
            )}
          </>
        )}

        {/* ════════════════════════════════════════════════════════════════════
            MODE SUCCESSION
            ════════════════════════════════════════════════════════════════════ */}
        {mode === 'succession' && (
          <>
            {!hResult ? (
              <View style={s.card}>
                <Text style={s.fieldLabel}>Région</Text>
                <View style={s.typeRow}>
                  {REGIONS_H.map((r) => (
                    <TouchableOpacity key={r.id} style={[s.typeBtn, hRegion === r.id && s.typeBtnActive]} onPress={() => setHRegion(r.id)}>
                      <Text style={[s.typeLabel, hRegion === r.id && s.typeLabelActive]}>{r.label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>

                <Text style={[s.fieldLabel, { marginTop: 14 }]}>Valeur de la succession (€)</Text>
                <TextInput
                  style={[s.textArea, { minHeight: 48, paddingTop: 10 }]}
                  keyboardType="numeric" placeholder="Ex: 250000"
                  placeholderTextColor={colors.textMuted}
                  value={estateValue} onChangeText={setEstate}
                />

                <Text style={[s.fieldLabel, { marginTop: 14 }]}>Lien familial de l'héritier</Text>
                <View style={s.chipRow}>
                  {HEIR_TYPES.map((h) => (
                    <TouchableOpacity key={h.id} style={[s.chip, heirType === h.id && s.chipActive]} onPress={() => setHeirType(h.id)}>
                      <Text style={[s.chipText, heirType === h.id && s.chipTextActive]}>{h.label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>

                <Text style={[s.fieldLabel, { marginTop: 14 }]}>Nombre d'héritiers</Text>
                <View style={s.typeRow}>
                  {['1', '2', '3', '4', '5+'].map((n) => (
                    <TouchableOpacity key={n} style={[s.typeBtn, numHeirs === n && s.typeBtnActive]} onPress={() => setNumHeirs(n === '5+' ? '5' : n)}>
                      <Text style={[s.typeLabel, numHeirs === n && s.typeLabelActive]}>{n}</Text>
                    </TouchableOpacity>
                  ))}
                </View>

                {hError && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {hError}</Text></View>}

                <TouchableOpacity activeOpacity={0.75}
                  style={[s.btn, { marginTop: 16 }, (!estateValue || hLoading) && s.btnDisabled]}
                  onPress={generateHeritage} disabled={!estateValue || hLoading}
                >
                  {hLoading ? <ActivityIndicator color="#FFF" /> : <Text style={s.btnText}>🏛️  Générer le guide</Text>}
                </TouchableOpacity>
              </View>
            ) : (
              <View style={s.card}>
                <ModelBadge model={hResult.model} />
                {hResult.summary && (
                  <View style={s.section}>
                    <Text style={s.sectionTitle}>Résumé</Text>
                    <Text style={s.bodyText}>{hResult.summary}</Text>
                  </View>
                )}
                {hResult.tax_estimate && (
                  <View style={[s.section, { backgroundColor: '#F0FDF4', borderRadius: 10, padding: 12 }]}>
                    <Text style={[s.sectionTitle, { color: '#27AE60' }]}>Estimation des droits</Text>
                    <Text style={[s.bodyText, { color: '#15803D', fontWeight: '700', fontSize: 16 }]}>
                      {typeof hResult.tax_estimate === 'number' ? `${hResult.tax_estimate.toLocaleString('fr-BE')} €` : hResult.tax_estimate}
                    </Text>
                  </View>
                )}
                {hResult.steps?.length > 0 && (
                  <View style={s.section}>
                    <Text style={s.sectionTitle}>Étapes à suivre</Text>
                    {hResult.steps.map((st, i) => (
                      <View key={i} style={s.stepItem}>
                        <View style={s.stepNumCircle}><Text style={s.stepNum}>{i + 1}</Text></View>
                        <Text style={s.stepText}>{typeof st === 'string' ? st : st.description || JSON.stringify(st)}</Text>
                      </View>
                    ))}
                  </View>
                )}
                {hResult.disclaimer && <Text style={s.disclaimer}>{hResult.disclaimer}</Text>}
                <TouchableOpacity style={[s.btn, { marginTop: 16 }]} onPress={() => { setHResult(null); setEstate(''); }}>
                  <Text style={s.btnText}>Nouvelle simulation</Text>
                </TouchableOpacity>
              </View>
            )}
          </>
        )}

        <View style={s.disclaimerBox}>
          <Text style={s.disclaimerBoxText}>⚖️ Lexavo est un outil d'information juridique. Il ne remplace pas un avocat.</Text>
        </View>

      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content:   { padding: 16, paddingBottom: 40 },

  heroHeader: { borderRadius: 16, padding: 20, marginBottom: 12, alignItems: 'center' },
  heroEmoji:  { fontSize: 32, marginBottom: 8 },
  heroTitle:  { fontSize: 20, fontWeight: '900', color: '#FFF', letterSpacing: 0.5 },
  heroSub:    { fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4, textAlign: 'center' },

  // Toggle 3 modes
  toggle: { flexDirection: 'row', backgroundColor: colors.surface, borderRadius: 12, padding: 4, marginBottom: 16, elevation: 2 },
  toggleBtn: { flex: 1, paddingVertical: 9, borderRadius: 8, alignItems: 'center' },
  toggleBtnActive: { backgroundColor: DIAG_ORANGE },
  toggleText: { fontSize: 11, fontWeight: '700', color: colors.textMuted },
  toggleTextActive: { color: '#FFF' },

  card: {
    backgroundColor: colors.surface, borderRadius: 16, padding: 16, marginBottom: 16,
    elevation: 3, shadowColor: colors.shadow, shadowOffset: { width: 0, height: 2 }, shadowOpacity: 1,
  },
  fieldLabel: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },

  typeRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  typeBtn: { flex: 1, borderRadius: 10, borderWidth: 1, borderColor: colors.border, padding: 10, alignItems: 'center', backgroundColor: colors.background },
  typeBtnActive: { borderColor: DIAG_ORANGE, backgroundColor: '#FFF7F5' },
  typeLabel: { fontSize: 11, fontWeight: '600', color: colors.textSecondary },
  typeLabelActive: { color: DIAG_ORANGE },

  textArea: {
    backgroundColor: colors.background, borderRadius: 10, padding: 12,
    fontSize: 14, color: colors.textPrimary, minHeight: 130,
    borderWidth: 1, borderColor: colors.border, lineHeight: 20, marginBottom: 12,
  },

  btn: { backgroundColor: DIAG_ORANGE, borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  btnDisabled: { opacity: 0.45 },
  btnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },

  errorBox: { backgroundColor: '#FEF2F2', borderRadius: 12, padding: 14, borderWidth: 1, borderColor: '#FCA5A5', marginBottom: 16 },
  errorText: { fontSize: 13, color: colors.error, fontWeight: '600' },

  // Score
  progressBar: { height: 6, backgroundColor: colors.border, borderRadius: 3, overflow: 'hidden', marginTop: 8 },
  progressFill: { height: 6, backgroundColor: '#F39C12', borderRadius: 3 },
  questionItem: { paddingVertical: 12 },
  questionBorder: { borderTopWidth: 1, borderTopColor: colors.border },
  questionRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 8 },
  qNumCircle: { width: 22, height: 22, borderRadius: 11, backgroundColor: DIAG_ORANGE, alignItems: 'center', justifyContent: 'center' },
  qNum: { color: '#FFF', fontSize: 11, fontWeight: '700' },
  questionText: { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 18 },
  answerRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  answerBtn: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1, borderColor: colors.border },
  answerBtnText: { fontSize: 11, fontWeight: '600' },
  scoreNum: { fontSize: 48, fontWeight: '900', textAlign: 'center', marginVertical: 8 },

  // Heritage
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 20, backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border },
  chipActive: { borderColor: '#8B4513', backgroundColor: '#FDF4EC' },
  chipText: { fontSize: 12, color: colors.textSecondary, fontWeight: '600' },
  chipTextActive: { color: '#8B4513' },

  // Résultats communs
  section: { marginBottom: 14 },
  sectionTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  bodyText: { fontSize: 14, color: colors.textPrimary, lineHeight: 21 },
  branchRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  branchPill: { backgroundColor: '#FFF7F5', borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4, borderWidth: 1, borderColor: '#FCCBB9' },
  branchText: { fontSize: 11, color: DIAG_ORANGE, fontWeight: '600' },
  listItem: { flexDirection: 'row', gap: 8, marginBottom: 6, alignItems: 'flex-start' },
  bullet: { fontSize: 13, marginTop: 1 },
  listText: { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 19 },
  stepItem: { flexDirection: 'row', gap: 10, marginBottom: 8, alignItems: 'flex-start' },
  stepNumCircle: { width: 22, height: 22, borderRadius: 11, backgroundColor: DIAG_ORANGE, alignItems: 'center', justifyContent: 'center' },
  stepNum: { color: '#FFF', fontSize: 11, fontWeight: '700' },
  stepText: { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 19 },
  urgencyBox: { borderRadius: 8, padding: 10, borderWidth: 1, marginBottom: 12, backgroundColor: '#FFFBEB' },
  urgencyText: { fontSize: 13, fontWeight: '600', color: colors.textPrimary },
  disclaimer: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic', textAlign: 'center' },

  disclaimerBox: { marginTop: 12, padding: 10, backgroundColor: '#FFFBEB', borderRadius: 8, borderWidth: 1, borderColor: '#FDE68A' },
  disclaimerBoxText: { fontSize: 10, color: '#92400E', textAlign: 'center', fontStyle: 'italic', lineHeight: 14 },
});
