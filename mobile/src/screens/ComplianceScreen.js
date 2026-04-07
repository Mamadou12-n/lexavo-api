/**
 * ComplianceScreen → Audit Entreprise
 * Fusionne Compliance (15 questions rapides) + Audit (30 questions approfondies).
 * Toggle "Rapide" vs "Approfondi".
 */

import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform, TextInput,
} from 'react-native';
import { getComplianceQuestions, runComplianceAudit, getAuditQuestions, generateAudit } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import { LinearGradient } from 'expo-linear-gradient';

const COMPLIANCE_TEAL = '#16A085';

const COMPLIANCE_COMPANY_TYPES = [
  { id: 'independant', label: '💼 Independant' },
  { id: 'srl',         label: '🏢 SRL' },
  { id: 'asbl',        label: '🤲 ASBL' },
];
const RISK_COLOR = { high: '#E74C3C', medium: '#F39C12', low: '#27AE60' };

const VERDICT_COLOR = { green: '#27AE60', orange: '#F39C12', red: '#E74C3C' };
const VERDICT_LABEL = { green: 'Conforme', orange: 'Conformite partielle', red: 'Non conforme' };
const AUDIT_ANSWER_OPTIONS = [
  { key: 'yes',     label: 'Oui',     color: '#27AE60' },
  { key: 'no',      label: 'Non',     color: '#E74C3C' },
  { key: 'partial', label: 'Partiel', color: '#F39C12' },
  { key: 'na',      label: 'N/A',     color: '#9CA3AF' },
];
const AUDIT_COMPANY_TYPES = [
  { key: 'srl',               label: 'SRL' },
  { key: 'sa',                label: 'SA' },
  { key: 'sc',                label: 'SC' },
  { key: 'independant',       label: 'Independant' },
  { key: 'asbl',              label: 'ASBL' },
  { key: 'pme',               label: 'PME' },
  { key: 'grande_entreprise', label: 'Grande entreprise' },
];

const MODE_RAPIDE = 'rapide';
const MODE_APPROFONDI = 'approfondi';

export default function ComplianceScreen() {
  const [mode, setMode] = useState(MODE_RAPIDE);

  // Compliance (Rapide)
  const [compQuestions, setCompQuestions]     = useState([]);
  const [compCompanyType, setCompCompanyType] = useState('srl');
  const [compAnswers, setCompAnswers]         = useState({});
  const [compFetching, setCompFetching]       = useState(true);
  const [compLoading, setCompLoading]         = useState(false);
  const [compResult, setCompResult]           = useState(null);
  const [compError, setCompError]             = useState(null);
  const [compPhotos, setCompPhotos]           = useState([]);

  // Audit (Approfondi)
  const [auditStep, setAuditStep]               = useState('form');
  const [auditCompanyType, setAuditCompanyType]  = useState('srl');
  const [auditCompanyName, setAuditCompanyName]  = useState('');
  const [auditQuestions, setAuditQuestions]       = useState([]);
  const [auditAnswers, setAuditAnswers]           = useState({});
  const [auditLoading, setAuditLoading]           = useState(false);
  const [auditResult, setAuditResult]             = useState(null);
  const [auditError, setAuditError]               = useState(null);

  useEffect(() => {
    getComplianceQuestions()
      .then((d) => setCompQuestions(d.questions ?? []))
      .catch(() => setCompQuestions([]))
      .finally(() => setCompFetching(false));
  }, []);

  const setCompAnswer = (id, val) => setCompAnswers((a) => ({ ...a, [id]: val }));

  const runCompliance = async () => {
    setCompLoading(true); setCompResult(null); setCompError(null);
    try {
      const data = await runComplianceAudit(compCompanyType, compAnswers);
      setCompResult(data);
    } catch (e) {
      setCompError(e.response?.data?.detail || e.message || 'Erreur reseau');
    } finally {
      setCompLoading(false);
    }
  };

  const loadAuditQuestions = async () => {
    setAuditLoading(true); setAuditError(null);
    try {
      const data = await getAuditQuestions(auditCompanyType);
      const q = data.questions ?? data ?? [];
      setAuditQuestions(q);
      const init = {};
      q.forEach((cat) => { (cat.questions ?? []).forEach((item) => { init[item.id] = null; }); });
      setAuditAnswers(init);
      setAuditStep('questions');
    } catch (e) {
      setAuditError(e.response?.data?.detail || e.message || 'Erreur chargement questions');
    } finally {
      setAuditLoading(false);
    }
  };

  const submitAudit = async () => {
    setAuditLoading(true); setAuditError(null);
    try {
      const formattedAnswers = Object.entries(auditAnswers)
        .filter(([, v]) => v !== null)
        .map(([qid, answer]) => ({ question_id: parseInt(qid, 10), answer }));
      const body = { answers: formattedAnswers, company_type: auditCompanyType, company_name: auditCompanyName || undefined };
      const data = await generateAudit(body);
      setAuditResult(data);
      setAuditStep('result');
    } catch (e) {
      setAuditError(e.response?.data?.detail || e.message || 'Erreur generation audit');
    } finally {
      setAuditLoading(false);
    }
  };

  const grouped = compQuestions.reduce((acc, q) => {
    const cat = q.category ?? 'General';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(q);
    return acc;
  }, {});
  const compAnsweredCount = Object.keys(compAnswers).length;
  const auditTotalQuestions = Object.keys(auditAnswers).length;
  const auditAnsweredCount  = Object.values(auditAnswers).filter((v) => v !== null).length;

  if (mode === MODE_RAPIDE && compFetching) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={COMPLIANCE_TEAL} size="large" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

      {/* Header + Toggle */}
      <LinearGradient colors={['#004D40', '#16A085']} style={styles.heroHeader}>
        <Text style={styles.heroEmoji}>🏢</Text>
        <Text style={styles.heroTitle}>Audit Entreprise</Text>
        <Text style={styles.heroSub}>
          {mode === MODE_RAPIDE ? '15 questions · 6 domaines' : '30 questions · 8 domaines'}
        </Text>
      </LinearGradient>

      <View style={styles.card}>
        <View style={styles.toggleRow}>
          <TouchableOpacity activeOpacity={0.75}
            style={[styles.toggleBtn, mode === MODE_RAPIDE && styles.toggleBtnActive]}
            onPress={() => setMode(MODE_RAPIDE)}
          >
            <Text style={[styles.toggleText, mode === MODE_RAPIDE && styles.toggleTextActive]}>
              ⚡ Rapide
            </Text>
          </TouchableOpacity>
          <TouchableOpacity activeOpacity={0.75}
            style={[styles.toggleBtn, mode === MODE_APPROFONDI && styles.toggleBtnActive]}
            onPress={() => setMode(MODE_APPROFONDI)}
          >
            <Text style={[styles.toggleText, mode === MODE_APPROFONDI && styles.toggleTextActive]}>
              🔎 Approfondi
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* ════════ MODE RAPIDE (Compliance) ════════ */}
      {mode === MODE_RAPIDE && (
        <>
          <View style={styles.card}>
            <Text style={styles.fieldLabel}>Type d'entreprise</Text>
            <View style={styles.typeRow}>
              {COMPLIANCE_COMPANY_TYPES.map((t) => (
                <TouchableOpacity activeOpacity={0.75}
                  key={t.id}
                  style={[styles.typeBtn, compCompanyType === t.id && styles.typeBtnActive]}
                  onPress={() => setCompCompanyType(t.id)}
                >
                  <Text style={[styles.typeLabel, compCompanyType === t.id && styles.typeLabelActive]}>
                    {t.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            <View style={styles.progressRow}>
              <Text style={styles.progressText}>{compAnsweredCount}/{compQuestions.length} questions</Text>
              <View style={styles.progressBar}>
                <View style={[styles.progressFill, { width: `${(compAnsweredCount / Math.max(compQuestions.length, 1)) * 100}%` }]} />
              </View>
            </View>
          </View>

          {Object.entries(grouped).map(([cat, qs]) => (
            <View key={cat} style={styles.card}>
              <Text style={styles.catTitle}>{cat}</Text>
              {qs.map((q, i) => (
                <View key={q.id ?? i} style={[styles.questionItem, i > 0 && styles.questionBorder]}>
                  <Text style={styles.questionText}>{q.question}</Text>
                  {q.legal_basis && <Text style={styles.questionLegal}>{q.legal_basis}</Text>}
                  <View style={styles.answerRow}>
                    {[
                      { id: 'oui', label: '✓ Oui', color: '#27AE60' },
                      { id: 'non', label: '✗ Non', color: '#E74C3C' },
                      { id: 'na', label: '— N/A', color: colors.textMuted },
                    ].map((opt) => (
                      <TouchableOpacity activeOpacity={0.75}
                        key={opt.id}
                        style={[styles.answerBtn, compAnswers[q.id ?? i] === opt.id && { backgroundColor: opt.color }]}
                        onPress={() => setCompAnswer(q.id ?? i, opt.id)}
                      >
                        <Text style={[styles.answerBtnText, { color: compAnswers[q.id ?? i] === opt.id ? '#FFF' : colors.textMuted }]}>
                          {opt.label}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              ))}
            </View>
          ))}

          <PhotoPicker photos={compPhotos} onPhotosChange={setCompPhotos} />

          <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, compLoading && styles.btnDisabled]}
            onPress={runCompliance}
            disabled={compLoading}
          >
            {compLoading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>✅  Generer l'audit rapide</Text>
            }
          </TouchableOpacity>

          {compError && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>⚠️ {compError}</Text>
            </View>
          )}

          {compResult && (
            <View style={styles.card}>
              <View style={[styles.scoreBanner, { backgroundColor: RISK_COLOR[compResult.risk_level] ?? COMPLIANCE_TEAL }]}>
                <Text style={styles.scoreVal}>{compResult.compliance_score}%</Text>
                <Text style={styles.scoreRisk}>{(compResult.risk_level ?? '').toUpperCase()}</Text>
              </View>
              {compResult.non_compliant_items?.length > 0 && (
                <View style={styles.section}>
                  <Text style={styles.sectionTitle}>Non-conformites ({compResult.non_compliant_items.length})</Text>
                  {compResult.non_compliant_items.map((item, i) => (
                    <View key={i} style={[styles.nonCompliantItem, { borderLeftColor: RISK_COLOR[item.risk] ?? colors.warning }]}>
                      <Text style={styles.ncQuestion}>{item.question}</Text>
                      {item.action_required && <Text style={styles.ncAction}>→ {item.action_required}</Text>}
                      {item.risk_description && <Text style={styles.ncRisk}>⚠️ {item.risk_description}</Text>}
                    </View>
                  ))}
                </View>
              )}
              {compResult.disclaimer && <Text style={styles.disclaimer}>{compResult.disclaimer}</Text>}
            </View>
          )}
        </>
      )}

      {/* ════════ MODE APPROFONDI (Audit) — form ════════ */}
      {mode === MODE_APPROFONDI && auditStep === 'form' && (
        <View style={styles.card}>
          <Text style={styles.label}>Nom de l'entreprise (optionnel)</Text>
          <TextInput
            style={styles.input}
            placeholder="Ex: Ma Societe SRL"
            placeholderTextColor={colors.textMuted}
            value={auditCompanyName}
            onChangeText={setAuditCompanyName}
          />
          <Text style={styles.label}>Type d'entreprise</Text>
          <View style={styles.chipRow}>
            {AUDIT_COMPANY_TYPES.map((ct) => (
              <TouchableOpacity activeOpacity={0.75}
                key={ct.key}
                style={[styles.chip, auditCompanyType === ct.key && styles.chipActive]}
                onPress={() => setAuditCompanyType(ct.key)}
              >
                <Text style={[styles.chipText, auditCompanyType === ct.key && styles.chipTextActive]}>
                  {ct.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
          <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, auditLoading && styles.btnDisabled]}
            onPress={loadAuditQuestions}
            disabled={auditLoading}
          >
            {auditLoading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>Demarrer l'audit approfondi</Text>
            }
          </TouchableOpacity>
          {auditError && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{auditError}</Text>
            </View>
          )}
        </View>
      )}

      {/* ════════ MODE APPROFONDI — questions ════════ */}
      {mode === MODE_APPROFONDI && auditStep === 'questions' && (
        <>
          <View style={styles.progressCard}>
            <Text style={styles.progressTextCenter}>{auditAnsweredCount} / {auditTotalQuestions} questions</Text>
            <View style={styles.progressBar}>
              <View style={[styles.progressFill, { width: `${auditTotalQuestions > 0 ? (auditAnsweredCount / auditTotalQuestions) * 100 : 0}%` }]} />
            </View>
          </View>

          {auditQuestions.map((cat, ci) => (
            <View key={ci} style={styles.card}>
              <Text style={styles.categoryTitle}>{cat.category ?? cat.name ?? `Categorie ${ci + 1}`}</Text>
              {(cat.questions ?? []).map((q) => (
                <View key={q.id} style={styles.questionBlock}>
                  <Text style={styles.questionText}>{q.text ?? q.question}</Text>
                  <View style={styles.answerRow}>
                    {AUDIT_ANSWER_OPTIONS.map((opt) => (
                      <TouchableOpacity activeOpacity={0.75}
                        key={opt.key}
                        style={[styles.auditAnswerBtn, auditAnswers[q.id] === opt.key && { backgroundColor: opt.color }]}
                        onPress={() => setAuditAnswers((prev) => ({ ...prev, [q.id]: opt.key }))}
                      >
                        <Text style={[styles.auditAnswerBtnText, auditAnswers[q.id] === opt.key && { color: '#FFF' }]}>
                          {opt.label}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              ))}
            </View>
          ))}

          {auditError && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{auditError}</Text>
            </View>
          )}

          <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, (auditLoading || auditAnsweredCount === 0) && styles.btnDisabled]}
            onPress={submitAudit}
            disabled={auditLoading || auditAnsweredCount === 0}
          >
            {auditLoading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>Lancer l'audit approfondi</Text>
            }
          </TouchableOpacity>

          <TouchableOpacity activeOpacity={0.75} style={styles.linkBtn} onPress={() => setAuditStep('form')}>
            <Text style={styles.linkBtnText}>Retour</Text>
          </TouchableOpacity>
        </>
      )}

      {/* ════════ MODE APPROFONDI — result ════════ */}
      {mode === MODE_APPROFONDI && auditStep === 'result' && auditResult && (() => {
        const verdictColor = VERDICT_COLOR[auditResult.verdict] ?? VERDICT_COLOR.orange;
        const verdictLabel = auditResult.verdict_label ?? VERDICT_LABEL[auditResult.verdict] ?? auditResult.verdict;
        return (
          <>
            <View style={styles.card}>
              <View style={styles.scoreContainer}>
                <View style={[styles.scoreCircle, { borderColor: verdictColor }]}>
                  <Text style={[styles.scoreValue, { color: verdictColor }]}>{auditResult.score ?? 0}</Text>
                  <Text style={styles.scoreMax}>/100</Text>
                </View>
                <View style={[styles.verdictBanner, { backgroundColor: verdictColor }]}>
                  <Text style={styles.verdictText}>{verdictLabel}</Text>
                </View>
              </View>
            </View>

            {auditResult.critical_risks?.length > 0 && (
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Risques critiques</Text>
                {auditResult.critical_risks.map((risk, i) => (
                  <View key={i} style={styles.riskItem}>
                    <Text style={styles.riskDot}>!!</Text>
                    <Text style={styles.riskText}>{typeof risk === 'string' ? risk : risk.description ?? risk.text}</Text>
                  </View>
                ))}
              </View>
            )}

            {auditResult.category_results && (
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Resultats par domaine</Text>
                {Object.entries(auditResult.category_results).map(([cat, data]) => (
                  <View key={cat} style={styles.catRow}>
                    <View style={[styles.catDot, { backgroundColor: VERDICT_COLOR[data.verdict] ?? '#9CA3AF' }]} />
                    <Text style={styles.catName}>{cat}</Text>
                    <Text style={[styles.catScore, { color: VERDICT_COLOR[data.verdict] ?? '#9CA3AF' }]}>{data.score}/100</Text>
                  </View>
                ))}
              </View>
            )}

            {auditResult.recommendations?.length > 0 && (
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Recommandations</Text>
                {auditResult.recommendations.map((rec, i) => (
                  <View key={i} style={styles.recCard}>
                    <View style={styles.recHeader}>
                      {rec.priority === 'high' && <Text style={styles.recPriorityHigh}>HAUTE</Text>}
                      {rec.priority === 'medium' && <Text style={styles.recPriorityMedium}>MOYENNE</Text>}
                      {rec.priority === 'low' && <Text style={styles.recPriorityLow}>BASSE</Text>}
                      {rec.deadline && <Text style={styles.recDeadline}>{rec.deadline}</Text>}
                    </View>
                    <Text style={styles.recAction}>{rec.action}</Text>
                    {rec.legal_ref && <Text style={styles.recLegal}>{rec.legal_ref}</Text>}
                  </View>
                ))}
              </View>
            )}

            <Text style={styles.disclaimer}>Cet audit est un outil d'orientation. Il ne remplace pas un conseil juridique professionnel.</Text>

            <TouchableOpacity activeOpacity={0.75} style={styles.linkBtn} onPress={() => { setAuditStep('form'); setAuditResult(null); }}>
              <Text style={styles.linkBtnText}>Nouvel audit</Text>
            </TouchableOpacity>
          </>
        );
      })()}

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

  heroHeader: { borderRadius: 16, padding: 20, marginBottom: 12, alignItems: 'center' },
  heroEmoji: { fontSize: 32, marginBottom: 8 },
  heroTitle: { fontSize: 20, fontWeight: '900', color: '#FFF', letterSpacing: 0.5 },
  heroSub: { fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4, textAlign: 'center' },

  card: {
    backgroundColor: colors.surface, borderRadius: 16, padding: 16,
    marginBottom: 12, elevation: 3, shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 }, shadowOpacity: 1,
  },
  featureHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 14 },
  featureEmoji: { fontSize: 28 },
  featureTitle: { fontSize: 15, fontWeight: '700', color: colors.textPrimary },
  featureSub: { fontSize: 12, color: colors.textMuted, marginTop: 1 },

  toggleRow: { flexDirection: 'row', gap: 8, backgroundColor: colors.surfaceAlt, borderRadius: 12, padding: 4 },
  toggleBtn: { flex: 1, paddingVertical: 10, borderRadius: 10, alignItems: 'center' },
  toggleBtnActive: { backgroundColor: COMPLIANCE_TEAL },
  toggleText: { fontSize: 13, fontWeight: '600', color: colors.textSecondary },
  toggleTextActive: { color: '#FFF' },

  fieldLabel: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  typeRow: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  typeBtn: { flex: 1, borderRadius: 10, borderWidth: 1, borderColor: colors.border, padding: 9, alignItems: 'center', backgroundColor: colors.background },
  typeBtnActive: { borderColor: COMPLIANCE_TEAL, backgroundColor: '#F0FDFB' },
  typeLabel: { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  typeLabelActive: { color: COMPLIANCE_TEAL },

  progressRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  progressText: { fontSize: 11, color: colors.textMuted, width: 80 },
  progressBar: { flex: 1, height: 4, backgroundColor: colors.border, borderRadius: 2 },
  progressFill: { height: 4, backgroundColor: COMPLIANCE_TEAL, borderRadius: 2 },

  catTitle: { fontSize: 13, fontWeight: '700', color: COMPLIANCE_TEAL, marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 },
  questionItem: { paddingVertical: 10 },
  questionBorder: { borderTopWidth: 1, borderTopColor: colors.border },
  questionText: { fontSize: 13, color: colors.textPrimary, lineHeight: 18, marginBottom: 4 },
  questionLegal: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic', marginBottom: 6 },

  answerRow: { flexDirection: 'row', gap: 6 },
  answerBtn: { borderRadius: 8, borderWidth: 1, borderColor: colors.border, paddingVertical: 5, paddingHorizontal: 10, backgroundColor: colors.background },
  answerBtnText: { fontSize: 11, fontWeight: '600' },

  btn: { backgroundColor: COMPLIANCE_TEAL, borderRadius: 12, paddingVertical: 14, alignItems: 'center', marginBottom: 12 },
  btnDisabled: { opacity: 0.45 },
  btnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },

  linkBtn: { alignItems: 'center', paddingVertical: 12 },
  linkBtnText: { color: colors.primary, fontSize: 14, fontWeight: '600' },

  errorBox: { backgroundColor: '#FEF2F2', borderRadius: 12, padding: 14, borderWidth: 1, borderColor: '#FCA5A5', marginBottom: 12 },
  errorText: { fontSize: 13, color: colors.error, fontWeight: '600' },

  scoreBanner: { borderRadius: 10, padding: 16, alignItems: 'center', marginBottom: 14 },
  scoreVal: { color: '#FFF', fontSize: 40, fontWeight: '900' },
  scoreRisk: { color: 'rgba(255,255,255,0.85)', fontSize: 14, fontWeight: '700', letterSpacing: 2, marginTop: 2 },

  section: { marginBottom: 12 },
  sectionTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },

  nonCompliantItem: { borderLeftWidth: 3, borderRadius: 6, padding: 10, marginBottom: 8, backgroundColor: '#FAFAFA' },
  ncQuestion: { fontSize: 12, fontWeight: '600', color: colors.textPrimary, marginBottom: 3 },
  ncAction: { fontSize: 12, color: colors.primary, lineHeight: 17, marginBottom: 2 },
  ncRisk: { fontSize: 11, color: colors.error, lineHeight: 16 },

  disclaimer: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic', textAlign: 'center' },

  // Audit styles
  label: { fontSize: 13, fontWeight: '600', color: colors.textSecondary, marginBottom: 6, marginTop: 10 },
  input: { backgroundColor: colors.background, borderRadius: 10, padding: 12, fontSize: 14, color: colors.textPrimary, borderWidth: 1, borderColor: colors.border, marginBottom: 8 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 },
  chip: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontSize: 12, color: colors.textSecondary, fontWeight: '600' },
  chipTextActive: { color: '#FFF' },

  progressCard: { backgroundColor: colors.surface, borderRadius: 12, padding: 14, marginBottom: 16 },
  progressTextCenter: { fontSize: 13, fontWeight: '600', color: colors.textSecondary, marginBottom: 8, textAlign: 'center' },
  categoryTitle: { fontSize: 14, fontWeight: '700', color: colors.primary, marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.5 },
  questionBlock: { marginBottom: 14 },

  auditAnswerBtn: { flex: 1, paddingVertical: 8, borderRadius: 8, backgroundColor: colors.surfaceAlt, alignItems: 'center', borderWidth: 1, borderColor: colors.border },
  auditAnswerBtnText: { fontSize: 11, fontWeight: '700', color: colors.textSecondary },

  scoreContainer: { alignItems: 'center', paddingVertical: 10 },
  scoreCircle: { width: 120, height: 120, borderRadius: 60, borderWidth: 6, alignItems: 'center', justifyContent: 'center', marginBottom: 14 },
  scoreValue: { fontSize: 36, fontWeight: '800' },
  scoreMax: { fontSize: 14, color: colors.textMuted, marginTop: -4 },
  verdictBanner: { borderRadius: 20, paddingHorizontal: 20, paddingVertical: 8 },
  verdictText: { color: '#FFF', fontSize: 14, fontWeight: '700' },

  riskItem: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 8 },
  riskDot: { fontSize: 12, color: '#E74C3C', fontWeight: '800', marginTop: 1 },
  riskText: { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 19 },

  catRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.border },
  catDot: { width: 10, height: 10, borderRadius: 5, marginRight: 10 },
  catName: { flex: 1, fontSize: 13, fontWeight: '600', color: colors.textPrimary, textTransform: 'capitalize' },
  catScore: { fontSize: 13, fontWeight: '700' },

  recCard: { backgroundColor: colors.surfaceAlt, borderRadius: 10, padding: 12, marginBottom: 10 },
  recHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  recPriorityHigh: { fontSize: 10, fontWeight: '800', color: '#E74C3C', backgroundColor: '#FEE2E2', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, overflow: 'hidden' },
  recPriorityMedium: { fontSize: 10, fontWeight: '800', color: '#F39C12', backgroundColor: '#FEF3C7', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, overflow: 'hidden' },
  recPriorityLow: { fontSize: 10, fontWeight: '800', color: '#27AE60', backgroundColor: '#D1FAE5', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, overflow: 'hidden' },
  recDeadline: { fontSize: 10, color: colors.textMuted, fontWeight: '600' },
  recAction: { fontSize: 13, color: colors.textPrimary, lineHeight: 19, marginBottom: 4 },
  recLegal: { fontSize: 11, color: colors.textMuted, fontStyle: 'italic' },
});
