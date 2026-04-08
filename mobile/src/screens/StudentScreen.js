/**
 * StudentScreen — Lexavo Campus v2
 * Dashboard gamifié : XP, Streak, Badges, 9 modes d'apprentissage, Groupes, Leaderboard
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform, Dimensions,
  Modal, Share, Alert,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import {
  generateQuiz, generateFlashcards, generateSummary, askQuestion,
  getStudentDashboard, postStudentActivity, getStudentLeaderboard,
  generateCaseStudy, evaluateCaseStudy, generateMockExam, submitMockExam,
  getStudentBadges, getStudentWeakBranches, generateFreeRecall,
  evaluateFreeRecall, generateInterleavedQuiz,
  createStudentGroup, joinStudentGroup, getStudentGroups,
} from '../api/client';
import Markdown from 'react-native-markdown-display';
import PhotoPicker from '../components/PhotoPicker';
import XPBar from '../components/XPBar';
import StreakCounter from '../components/StreakCounter';
import BadgeGrid from '../components/BadgeGrid';

const { width: SW } = Dimensions.get('window');
const XP_PER_LEVEL = 500;

// ─── Design System ───────────────────────────────────────────────────────────
const T = {
  bg: '#080B14', surface: '#0F1629', surfaceAlt: '#141D33', elevated: '#1A2440',
  border: '#1E2A45', borderLit: '#2A3A5C',
  neon1: '#00D4AA', neon2: '#8B5CF6', neon3: '#FF6B6B', neon4: '#FFB84D', neon5: '#4DA6FF',
  white: '#F0F4FF', muted: '#5A6B8A', dimmed: '#3A4A6A',
  glow1: 'rgba(0, 212, 170, 0.12)', glow2: 'rgba(139, 92, 246, 0.12)', glow3: 'rgba(255, 107, 107, 0.12)',
};

const BRANCHES = [
  'Droit du travail', 'Droit familial', 'Droit fiscal', 'Droit pénal',
  'Droit civil', 'Droit administratif', 'Droit commercial', 'Droit immobilier',
  'Propriété intellectuelle', 'Sécurité sociale', 'Droit des étrangers',
  'Droit européen', 'Marchés publics', 'Environnement', 'Droits fondamentaux',
];

const MODES = [
  { id: 'quiz', label: 'Quiz IA', sub: 'L\'IA s\'adapte à ton niveau.', gradient: ['#4A1D96', '#8B5CF6'], glowColor: 'rgba(139, 92, 246, 0.25)', icon: '⚡', badge: '+50 XP', xpMode: 'quiz_pass' },
  { id: 'flashcards', label: 'Flashcards SRS', sub: 'Algorithme Leitner. Mémorise moins, retiens plus.', gradient: ['#004D8F', '#4DA6FF'], glowColor: 'rgba(77, 166, 255, 0.25)', icon: '🃏', badge: '+20 XP', xpMode: 'flashcards' },
  { id: 'summary', label: 'Résumé Turbo', sub: 'Des heures de cours en 30 secondes.', gradient: ['#991B1B', '#FF6B6B'], glowColor: 'rgba(255, 107, 107, 0.25)', icon: '🚀', badge: '+10 XP', xpMode: 'summary' },
  { id: 'chat', label: 'Tuteur IA', sub: 'Ton prof 24/7. Pose n\'importe quelle question.', gradient: ['#004D40', '#00D4AA'], glowColor: 'rgba(0, 212, 170, 0.25)', icon: '🤖', badge: 'ILLIMITÉ', xpMode: null },
  { id: 'podcast', label: 'Podcast IA', sub: 'Révise dans le métro. Bientôt disponible.', gradient: ['#7C4D00', '#FFB84D'], glowColor: 'rgba(255, 184, 77, 0.25)', icon: '🎙️', badge: 'BIENTÔT', xpMode: null, disabled: true },
  { id: 'case_study', label: 'Cas Pratique', sub: 'Résoudre un cas réel. Correction IA enrichie.', gradient: ['#1A4731', '#2DD4BF'], glowColor: 'rgba(45, 212, 191, 0.25)', icon: '🧠', badge: '+75 XP', xpMode: 'case_study' },
  { id: 'mock_exam', label: 'Examen Blanc', sub: '20 questions chrono. Solo ou groupe.', gradient: ['#4A1A1A', '#E53E3E'], glowColor: 'rgba(229, 62, 62, 0.25)', icon: '📝', badge: '+150 XP', xpMode: 'mock_exam' },
  { id: 'interleaved', label: 'Révision Mixte', sub: 'Mélange de branches. +50% de rétention prouvé.', gradient: ['#1A1A4A', '#6366F1'], glowColor: 'rgba(99, 102, 241, 0.25)', icon: '🔀', badge: '+50 XP', xpMode: 'quiz_pass' },
  { id: 'free_recall', label: 'Rappel Libre', sub: 'Question ouverte. ×2 rétention vs QCM.', gradient: ['#2D1A4A', '#A855F7'], glowColor: 'rgba(168, 85, 247, 0.25)', icon: '✍️', badge: '+75 XP', xpMode: 'free_recall' },
];

// ─── Composant principal ──────────────────────────────────────────────────────
export default function StudentScreen() {
  // Navigation interne
  const [view, setView] = useState('dashboard'); // 'dashboard' | mode.id | 'branch_select'
  const [activeMode, setActiveMode] = useState(null);
  const [branch, setBranch] = useState(null);

  // Dashboard data
  const [dash, setDash] = useState(null);
  const [weakBranches, setWeakBranches] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [badges, setBadges] = useState([]);
  const [lbScope, setLbScope] = useState('global');
  const [dashLoading, setDashLoading] = useState(false);

  // Modes communs
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [topic, setTopic] = useState('');
  const [photos, setPhotos] = useState([]);

  // Quiz / Flashcards
  const [flippedCards, setFlipped] = useState({});
  const [selectedAnswers, setSelected] = useState({});
  const [showCorrections, setShowCorr] = useState(false);

  // Chat
  const [messages, setMessages] = useState([{ role: 'assistant', content: 'Salut ! Je suis ton tuteur IA en droit belge.\n\nPose-moi n\'importe quelle question, ou photographie tes notes.' }]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatScrollRef = useRef(null);

  // Cas pratique
  const [caseData, setCaseData] = useState(null);
  const [caseAnswer, setCaseAnswer] = useState('');
  const [caseStep, setCaseStep] = useState('config'); // config|writing|result
  const [caseDifficulty, setCaseDifficulty] = useState('moyen');

  // Examen blanc
  const [examData, setExamData] = useState(null);
  const [examAnswers, setExamAnswers] = useState({});
  const [examStep, setExamStep] = useState('config'); // config|exam|result
  const [examResult, setExamResult] = useState(null);
  const [examTimer, setExamTimer] = useState(20 * 60);
  const [examBranches, setExamBranches] = useState([]);
  const timerRef = useRef(null);
  const submitExamRef = useRef(null); // ref pour éviter stale closure dans le timer

  // Rappel libre
  const [recallQuestion, setRecallQuestion] = useState(null);
  const [recallAnswer, setRecallAnswer] = useState('');
  const [recallResult, setRecallResult] = useState(null);
  const [recallStep, setRecallStep] = useState('config'); // config|writing|result

  // Révision mixte
  const [mixBranches, setMixBranches] = useState([]);
  const [mixResult, setMixResult] = useState(null);
  const [mixAnswers, setMixAnswers] = useState({});
  const [mixCorrections, setMixCorrections] = useState(false);

  // XP animation
  const [xpEarned, setXpEarned] = useState(null);
  const [newBadges, setNewBadges] = useState([]);

  // Groupes
  const [groups, setGroups] = useState([]);
  const [groupModal, setGroupModal] = useState(false);
  const [groupName, setGroupName] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [groupTab, setGroupTab] = useState('list'); // list | create | join

  // ─── Chargement dashboard ───────────────────────────────────────────────────
  const loadDashboard = useCallback(async () => {
    setDashLoading(true);
    try {
      const [d, wb, lb, bg] = await Promise.all([
        getStudentDashboard().catch(() => null),
        getStudentWeakBranches().catch(() => []),
        getStudentLeaderboard('global').catch(() => []),
        getStudentBadges().catch(() => ({ available: [], earned_ids: [] })),
      ]);
      if (d) setDash(d);
      setWeakBranches(wb?.branches || []);
      setLeaderboard(lb?.leaderboard || []);
      setBadges(bg);
    } catch (_) {}
    finally { setDashLoading(false); }
  }, []);

  useEffect(() => { if (view === 'dashboard') loadDashboard(); }, [view]);

  useEffect(() => {
    if (lbScope !== 'global') return;
    getStudentLeaderboard('global').then(d => setLeaderboard(d?.leaderboard || [])).catch(() => {});
  }, [lbScope]);

  // Timer examen blanc — submitExamRef évite le stale closure
  useEffect(() => {
    if (examStep !== 'exam') return;
    timerRef.current = setInterval(() => {
      setExamTimer(t => {
        if (t <= 1) { clearInterval(timerRef.current); submitExamRef.current?.(); return 0; }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, [examStep]);

  // ─── Helpers ────────────────────────────────────────────────────────────────
  const fmtTime = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  const goMode = (m) => {
    if (m.disabled) { Alert.alert('Bientôt', 'Cette fonctionnalité arrive bientôt !'); return; }
    setActiveMode(m);
    setResult(null); setError(null); setBranch(null); setTopic(''); setPhotos([]);
    setSelected({}); setShowCorr(false); setFlipped({});
    if (m.id === 'interleaved') { setView('interleaved'); return; }
    if (m.id === 'case_study') { setCaseStep('config'); setView('case_study'); return; }
    if (m.id === 'mock_exam') { setExamStep('config'); setExamBranches([]); setView('mock_exam'); return; }
    if (m.id === 'free_recall') { setRecallStep('config'); setView('free_recall'); return; }
    setView('branch_select');
  };

  const backToDash = () => {
    setView('dashboard');
    setActiveMode(null); setBranch(null); setResult(null); setError(null);
    setCaseStep('config'); setExamStep('config'); setRecallStep('config');
    setExamData(null); setCaseData(null); setRecallQuestion(null);
    setMixBranches([]); setMixResult(null);
    clearInterval(timerRef.current);
  };

  const awardXP = async (mode, score, total) => {
    try {
      const r = await postStudentActivity(mode, branch || 'Général', score, total);
      if (r?.xp_earned > 0) setXpEarned(r.xp_earned);
      if (r?.new_badges?.length > 0) setNewBadges(r.new_badges);
      loadDashboard();
    } catch (_) {}
  };

  const getScore = () => {
    if (!result?.questions) return { correct: 0, total: 0 };
    let c = 0;
    result.questions.forEach(q => { if (selectedAnswers[q.id] === q.correct) c++; });
    return { correct: c, total: result.questions.length };
  };

  // ─── Génération quiz/flashcards/résumé ─────────────────────────────────────
  const generate = async () => {
    if (!branch) { setError('Sélectionne une branche du droit.'); return; }
    setLoading(true); setResult(null); setError(null);
    setSelected({}); setShowCorr(false); setFlipped({});
    try {
      let data;
      if (activeMode.id === 'quiz') data = await generateQuiz(branch, 'moyen', 10);
      else if (activeMode.id === 'flashcards') data = await generateFlashcards(branch, topic, 12);
      else data = await generateSummary(branch, topic || branch);
      setResult(data);
      setView(activeMode.id);
    } catch (e) { setError(e.response?.data?.detail || e.message || 'Erreur réseau'); }
    finally { setLoading(false); }
  };

  const submitQuiz = async () => {
    setShowCorr(true);
    const { correct, total } = getScore();
    await awardXP(correct / total >= 1 ? 'quiz_perfect' : 'quiz_pass', correct, total);
  };

  const sendChat = async () => {
    const text = chatInput.trim();
    if (!text && photos.length === 0) return;
    setMessages(prev => [...prev, { role: 'user', content: text || '[Photo envoyée]' }]);
    setChatInput(''); setChatLoading(true);
    try {
      const data = await askQuestion(text || 'Analyse ces notes', { photos, top_k: 4 });
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
      setPhotos([]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Erreur : ' + (e.response?.data?.detail || e.message) }]);
    } finally {
      setChatLoading(false);
      setTimeout(() => chatScrollRef.current?.scrollToEnd({ animated: true }), 200);
    }
  };

  // ─── Cas pratique ──────────────────────────────────────────────────────────
  const startCaseStudy = async () => {
    if (!branch) { setError('Sélectionne une branche.'); return; }
    setLoading(true); setCaseData(null); setError(null);
    try {
      const d = await generateCaseStudy(branch, caseDifficulty);
      setCaseData(d); setCaseStep('writing'); setCaseAnswer('');
    } catch (e) { setError(e.response?.data?.detail || e.message || 'Erreur'); }
    finally { setLoading(false); }
  };

  const submitCaseStudy = async () => {
    if (caseAnswer.trim().length < 50) { setError('Réponse trop courte (min. 50 caractères).'); return; }
    setLoading(true); setError(null);
    try {
      const r = await evaluateCaseStudy(caseData, caseAnswer);
      setCaseData(prev => ({ ...prev, evaluation: r }));
      setCaseStep('result');
      await awardXP('case_study', r.score || 7, 10);
    } catch (e) { setError(e.response?.data?.detail || e.message || 'Erreur'); }
    finally { setLoading(false); }
  };

  // ─── Examen blanc ──────────────────────────────────────────────────────────
  const startMockExam = async () => {
    if (examBranches.length === 0) { setError('Sélectionne au moins une branche.'); return; }
    setLoading(true); setExamData(null); setError(null); setExamAnswers({});
    try {
      const d = await generateMockExam(examBranches, 20);
      setExamData(d); setExamStep('exam'); setExamTimer(20 * 60);
    } catch (e) { setError(e.response?.data?.detail || e.message || 'Erreur'); }
    finally { setLoading(false); }
  };

  const submitExam = async () => {
    clearInterval(timerRef.current);
    setLoading(true);
    try {
      const r = await submitMockExam(examData, examAnswers);
      setExamResult(r); setExamStep('result');
      await awardXP('mock_exam', r.score || 10, 20);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };
  // Garder la ref à jour à chaque render pour éviter le stale closure dans le timer
  submitExamRef.current = submitExam;

  // ─── Rappel libre ──────────────────────────────────────────────────────────
  const startFreeRecall = async () => {
    if (!branch) { setError('Sélectionne une branche.'); return; }
    setLoading(true); setRecallQuestion(null); setError(null);
    try {
      const d = await generateFreeRecall(branch);
      setRecallQuestion(d); setRecallStep('writing'); setRecallAnswer('');
    } catch (e) { setError(e.response?.data?.detail || e.message || 'Erreur'); }
    finally { setLoading(false); }
  };

  const submitFreeRecall = async () => {
    if (recallAnswer.trim().length < 20) { setError('Réponse trop courte.'); return; }
    setLoading(true); setError(null);
    try {
      const r = await evaluateFreeRecall(recallQuestion, recallAnswer);
      setRecallResult(r); setRecallStep('result');
      await awardXP('free_recall', r.score || 7, 10);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  // ─── Révision mixte ────────────────────────────────────────────────────────
  const startInterleaved = async () => {
    if (mixBranches.length < 2) { setError('Sélectionne au moins 2 branches.'); return; }
    setLoading(true); setMixResult(null); setMixAnswers({}); setMixCorrections(false); setError(null);
    try {
      const d = await generateInterleavedQuiz(mixBranches);
      setMixResult(d);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const submitInterleaved = async () => {
    setMixCorrections(true);
    if (!mixResult?.questions) return;
    let correct = 0;
    mixResult.questions.forEach(q => { if (mixAnswers[q.id] === q.correct) correct++; });
    await awardXP('quiz_pass', correct, mixResult.questions.length);
  };

  const toggleMixBranch = (b) => {
    setMixBranches(prev => prev.includes(b) ? prev.filter(x => x !== b) : prev.length < 5 ? [...prev, b] : prev);
  };

  const toggleExamBranch = (b) => {
    setExamBranches(prev => prev.includes(b) ? prev.filter(x => x !== b) : prev.length < 3 ? [...prev, b] : prev);
  };

  // ─── Groupes ───────────────────────────────────────────────────────────────
  const loadGroups = async () => {
    try { const g = await getStudentGroups(); setGroups(g?.groups || []); } catch (_) {}
  };

  const handleCreateGroup = async () => {
    if (!groupName.trim()) return;
    try {
      const g = await createStudentGroup(groupName.trim());
      Alert.alert('Groupe créé !', `Code d\'invitation : ${g.code}\nPartage ce code avec tes amis.`);
      setGroupName(''); setGroupTab('list'); loadGroups();
    } catch (e) { Alert.alert('Erreur', e.message); }
  };

  const handleJoinGroup = async () => {
    if (!joinCode.trim()) return;
    try {
      await joinStudentGroup(joinCode.trim().toUpperCase());
      Alert.alert('Rejoint !', 'Tu as rejoint le groupe.'); setJoinCode(''); setGroupTab('list'); loadGroups();
    } catch (e) { Alert.alert('Erreur', e.message); }
  };

  const shareResult = async (label) => {
    try { await Share.share({ message: `🎓 Lexavo Campus — ${label}\n\nTélécharge l\'app Lexavo pour étudier le droit belge !` }); }
    catch (_) {}
  };

  // ─── XP notification overlay ────────────────────────────────────────────────
  const XPNotif = () => {
    if (!xpEarned && !newBadges.length) return null;
    return (
      <TouchableOpacity style={s.xpNotif} onPress={() => { setXpEarned(null); setNewBadges([]); }}>
        {xpEarned > 0 && <Text style={s.xpNotifText}>+{xpEarned} XP</Text>}
        {newBadges.map(b => (
          <Text key={b.badge_id} style={s.xpNotifBadge}>{b.badge_emoji} {b.badge_name}</Text>
        ))}
        <Text style={s.xpNotifDismiss}>Touche pour fermer</Text>
      </TouchableOpacity>
    );
  };

  // ════════════════════════════════════════════════════════════════════════════
  //  RENDER
  // ════════════════════════════════════════════════════════════════════════════

  // ─── Sélection branche ─────────────────────────────────────────────────────
  if (view === 'branch_select') {
    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll}>
          <BackBtn onPress={backToDash} />
          <View style={s.branchHeader}>
            <LinearGradient colors={activeMode?.gradient || [T.neon1, T.neon2]} style={s.branchBadge}>
              <Text style={{ fontSize: 16 }}>{activeMode?.icon}</Text>
              <Text style={s.branchBadgeText}>{activeMode?.label}</Text>
            </LinearGradient>
            <Text style={s.secTitle}>Choisis ta branche</Text>
          </View>
          <View style={s.branchGrid}>
            {BRANCHES.map(b => (
              <TouchableOpacity key={b} activeOpacity={0.75} style={[s.branchChip, branch === b && s.branchActive]} onPress={() => setBranch(b)}>
                <Text style={[s.branchText, branch === b && s.branchTextActive]}>{b}</Text>
              </TouchableOpacity>
            ))}
          </View>
          {(activeMode?.id === 'flashcards' || activeMode?.id === 'summary') && (
            <View style={s.inputWrap}>
              <Text style={s.inputLabel}>Sujet précis (optionnel)</Text>
              <TextInput style={s.input} placeholder="Ex: licenciement pour motif grave" placeholderTextColor={T.dimmed} value={topic} onChangeText={setTopic} />
            </View>
          )}
          {activeMode?.id !== 'chat' && (
            <View style={{ marginHorizontal: 16 }}>
              <PhotoPicker photos={photos} onPhotosChange={setPhotos} label="📷 Photographier tes notes" />
            </View>
          )}
          {error && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {error}</Text></View>}
          <TouchableOpacity activeOpacity={0.85} style={s.genWrap} onPress={generate} disabled={loading || !branch}>
            <LinearGradient colors={activeMode?.gradient || [T.neon1, T.neon2]} style={[s.genBtn, !branch && { opacity: 0.5 }]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}>
              {loading ? <ActivityIndicator color="#FFF" /> : (
                <Text style={s.genBtnText}>
                  {activeMode?.id === 'quiz' ? '⚡ Lancer le quiz' : activeMode?.id === 'flashcards' ? '🃏 Générer les cartes' : '🚀 Synthétiser'}
                </Text>
              )}
            </LinearGradient>
          </TouchableOpacity>
        </ScrollView>
      </View>
    );
  }

  // ─── Quiz ──────────────────────────────────────────────────────────────────
  if (view === 'quiz' && result) {
    const { correct, total } = showCorrections ? getScore() : { correct: 0, total: 0 };
    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll}>
          <BackBtn onPress={backToDash} />
          {!showCorrections ? (
            <>
              <Text style={s.modeTitle}>⚡ Quiz — {branch}</Text>
              {result.questions?.map((q, i) => (
                <View key={q.id} style={s.quizCard}>
                  <Text style={s.quizQ}>{i + 1}. {q.question}</Text>
                  {q.options?.map(o => (
                    <TouchableOpacity key={o} style={[s.optBtn, selectedAnswers[q.id] === o && s.optSelected]} onPress={() => setSelected(p => ({ ...p, [q.id]: o }))}>
                      <Text style={[s.optText, selectedAnswers[q.id] === o && { color: T.neon1 }]}>{o}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              ))}
              <TouchableOpacity style={s.genWrap} onPress={submitQuiz} disabled={Object.keys(selectedAnswers).length === 0}>
                <LinearGradient colors={['#4A1D96', '#8B5CF6']} style={s.genBtn} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}>
                  <Text style={s.genBtnText}>Vérifier mes réponses</Text>
                </LinearGradient>
              </TouchableOpacity>
            </>
          ) : (
            <>
              <Text style={s.modeTitle}>Résultats : {correct}/{total}</Text>
              {result.questions?.map((q, i) => {
                const chosen = selectedAnswers[q.id];
                const ok = chosen === q.correct;
                return (
                  <View key={q.id} style={[s.quizCard, { borderColor: ok ? T.neon1 : T.neon3 }]}>
                    <Text style={s.quizQ}>{i + 1}. {q.question}</Text>
                    <Text style={{ color: ok ? T.neon1 : T.neon3, marginTop: 4, fontSize: 13 }}>
                      {ok ? '✓ Correct' : `✗ Tu as choisi: ${chosen || '—'}`}
                    </Text>
                    {!ok && <Text style={{ color: T.neon1, fontSize: 13, marginTop: 2 }}>Bonne réponse : {q.correct}</Text>}
                    {q.explanation && <Text style={{ color: T.muted, fontSize: 12, marginTop: 6 }}>{q.explanation}</Text>}
                  </View>
                );
              })}
              {xpEarned && <Text style={s.xpInline}>+{xpEarned} XP gagnés !</Text>}
              <ActionRow onShare={() => shareResult(`Quiz ${branch} : ${correct}/${total}`)} onBack={backToDash} />
            </>
          )}
        </ScrollView>
        <XPNotif />
      </View>
    );
  }

  // ─── Flashcards ────────────────────────────────────────────────────────────
  if (view === 'flashcards' && result) {
    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll}>
          <BackBtn onPress={backToDash} />
          <Text style={s.modeTitle}>🃏 Flashcards — {branch}</Text>
          <Text style={[s.muted, { textAlign: 'center', marginBottom: 16 }]}>Touche pour retourner la carte</Text>
          {result.cards?.map((c, i) => (
            <TouchableOpacity key={c.id || i} activeOpacity={0.85} style={[s.flashCard, flippedCards[c.id] && s.flashCardFlipped]} onPress={() => setFlipped(p => ({ ...p, [c.id]: !p[c.id] }))}>
              <LinearGradient colors={flippedCards[c.id] ? ['#004D40', '#00D4AA'] : ['#004D8F', '#4DA6FF']} style={s.flashCardInner}>
                <Text style={s.flashLabel}>{flippedCards[c.id] ? 'Définition' : 'Concept'}</Text>
                <Text style={s.flashText}>{flippedCards[c.id] ? c.back : c.front}</Text>
                {c.article && flippedCards[c.id] && <Text style={s.flashArticle}>📖 {c.article}</Text>}
              </LinearGradient>
            </TouchableOpacity>
          ))}
          <ActionRow onShare={() => shareResult(`${result.cards?.length} flashcards ${branch}`)} onBack={backToDash} />
        </ScrollView>
        <XPNotif />
      </View>
    );
  }

  // ─── Résumé ────────────────────────────────────────────────────────────────
  if (view === 'summary' && result) {
    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll}>
          <BackBtn onPress={backToDash} />
          <Text style={s.modeTitle}>🚀 Résumé — {branch}</Text>
          <View style={s.summaryCard}>
            <Markdown style={mdStyle}>{result.summary || result.content || JSON.stringify(result)}</Markdown>
          </View>
          <ActionRow onShare={() => shareResult(`Résumé ${branch}`)} onBack={backToDash} />
        </ScrollView>
        <XPNotif />
      </View>
    );
  }

  // ─── Tuteur IA ─────────────────────────────────────────────────────────────
  if (view === 'chat') {
    return (
      <View style={s.root}>
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
          <ScrollView contentContainerStyle={s.scroll} ref={chatScrollRef} keyboardShouldPersistTaps="handled">
            <BackBtn onPress={backToDash} />
            <Text style={s.modeTitle}>🤖 Tuteur IA</Text>
            {messages.map((m, i) => (
              <View key={i} style={[s.bubble, m.role === 'user' ? s.bubbleUser : s.bubbleAI]}>
                {m.role === 'assistant' ? <Markdown style={mdStyle}>{m.content}</Markdown> : <Text style={{ color: T.white, fontSize: 14 }}>{m.content}</Text>}
              </View>
            ))}
            {chatLoading && <ActivityIndicator color={T.neon1} style={{ margin: 16 }} />}
            <PhotoPicker photos={photos} onPhotosChange={setPhotos} />
          </ScrollView>
          <View style={s.chatBar}>
            <TextInput style={s.chatInput} placeholder="Pose ta question..." placeholderTextColor={T.dimmed} value={chatInput} onChangeText={setChatInput} multiline />
            <TouchableOpacity onPress={sendChat} style={s.chatSend}>
              <LinearGradient colors={[T.neon1, T.neon2]} style={s.chatSendGrad}>
                <Text style={{ color: '#FFF', fontWeight: '700', fontSize: 16 }}>→</Text>
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </View>
    );
  }

  // ─── Cas pratique ──────────────────────────────────────────────────────────
  if (view === 'case_study') {
    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
          <BackBtn onPress={backToDash} />
          <Text style={s.modeTitle}>🧠 Cas Pratique</Text>

          {caseStep === 'config' && (
            <>
              <Text style={s.secLabel}>BRANCHE DU DROIT</Text>
              <View style={s.branchGrid}>
                {BRANCHES.map(b => (
                  <TouchableOpacity key={b} style={[s.branchChip, branch === b && s.branchActive]} onPress={() => setBranch(b)}>
                    <Text style={[s.branchText, branch === b && s.branchTextActive]}>{b}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              <Text style={s.secLabel}>DIFFICULTÉ</Text>
              <View style={s.rowCentered}>
                {['facile', 'moyen', 'difficile'].map(d => (
                  <TouchableOpacity key={d} style={[s.diffChip, caseDifficulty === d && s.diffActive]} onPress={() => setCaseDifficulty(d)}>
                    <Text style={[s.diffText, caseDifficulty === d && { color: T.neon1 }]}>{d}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              {error && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {error}</Text></View>}
              <TouchableOpacity style={s.genWrap} onPress={startCaseStudy} disabled={loading || !branch}>
                <LinearGradient colors={['#1A4731', '#2DD4BF']} style={[s.genBtn, (!branch || loading) && { opacity: 0.5 }]}>
                  {loading ? <ActivityIndicator color="#FFF" /> : <Text style={s.genBtnText}>🧠 Générer un cas</Text>}
                </LinearGradient>
              </TouchableOpacity>
            </>
          )}

          {caseStep === 'writing' && caseData && (
            <>
              <View style={s.caseCard}>
                <Text style={s.caseLabel}>FAITS</Text>
                <Text style={s.caseText}>{caseData.facts}</Text>
              </View>
              <View style={s.caseCard}>
                <Text style={s.caseLabel}>QUESTIONS</Text>
                {caseData.questions?.map((q, i) => <Text key={i} style={[s.caseText, { color: T.neon4 }]}>{i + 1}. {q}</Text>)}
              </View>
              <Text style={s.inputLabel}>Ta réponse (minimum 50 caractères)</Text>
              <TextInput
                style={[s.input, { height: 160, textAlignVertical: 'top' }]}
                multiline placeholder="Développe ton raisonnement juridique..."
                placeholderTextColor={T.dimmed} value={caseAnswer} onChangeText={setCaseAnswer}
              />
              {error && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {error}</Text></View>}
              <TouchableOpacity style={s.genWrap} onPress={submitCaseStudy} disabled={loading}>
                <LinearGradient colors={['#1A4731', '#2DD4BF']} style={s.genBtn}>
                  {loading ? <ActivityIndicator color="#FFF" /> : <Text style={s.genBtnText}>Soumettre ma réponse</Text>}
                </LinearGradient>
              </TouchableOpacity>
            </>
          )}

          {caseStep === 'result' && caseData?.evaluation && (
            <>
              <View style={[s.caseCard, { borderColor: T.neon1 }]}>
                <Text style={[s.caseLabel, { color: T.neon1 }]}>CORRECTION IA</Text>
                <Text style={s.caseText}>Note : {caseData.evaluation.score}/10</Text>
                <Text style={[s.caseText, { marginTop: 8 }]}>{caseData.evaluation.feedback}</Text>
                {caseData.evaluation.articles_cited?.length > 0 && (
                  <Text style={{ color: T.neon4, marginTop: 8 }}>📖 Articles : {caseData.evaluation.articles_cited.join(', ')}</Text>
                )}
              </View>
              {xpEarned && <Text style={s.xpInline}>+{xpEarned} XP gagnés !</Text>}
              <ActionRow onShare={() => shareResult(`Cas pratique ${branch} : ${caseData.evaluation.score}/10`)} onBack={backToDash} />
            </>
          )}
        </ScrollView>
        <XPNotif />
      </View>
    );
  }

  // ─── Examen blanc ──────────────────────────────────────────────────────────
  if (view === 'mock_exam') {
    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll}>
          {examStep !== 'exam' && <BackBtn onPress={backToDash} />}
          <Text style={s.modeTitle}>📝 Examen Blanc</Text>

          {examStep === 'config' && (
            <>
              <Text style={s.secLabel}>BRANCHES (max 3)</Text>
              <View style={s.branchGrid}>
                {BRANCHES.map(b => (
                  <TouchableOpacity key={b} style={[s.branchChip, examBranches.includes(b) && s.branchActive]} onPress={() => toggleExamBranch(b)}>
                    <Text style={[s.branchText, examBranches.includes(b) && s.branchTextActive]}>{b}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              {error && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {error}</Text></View>}
              <TouchableOpacity style={s.genWrap} onPress={startMockExam} disabled={loading || examBranches.length === 0}>
                <LinearGradient colors={['#4A1A1A', '#E53E3E']} style={[s.genBtn, (loading || !examBranches.length) && { opacity: 0.5 }]}>
                  {loading ? <ActivityIndicator color="#FFF" /> : <Text style={s.genBtnText}>📝 Lancer l'examen (20 min)</Text>}
                </LinearGradient>
              </TouchableOpacity>
            </>
          )}

          {examStep === 'exam' && examData && (
            <>
              <View style={s.timerRow}>
                <Text style={[s.timerText, examTimer < 180 && { color: T.neon3 }]}>⏱ {fmtTime(examTimer)}</Text>
                <Text style={s.muted}>{Object.keys(examAnswers).length}/{examData.questions?.length} répondues</Text>
              </View>
              {examData.questions?.map((q, i) => (
                <View key={q.id || i} style={s.quizCard}>
                  <Text style={s.quizQ}>{i + 1}. {q.question}</Text>
                  {q.options?.map(o => (
                    <TouchableOpacity key={o} style={[s.optBtn, examAnswers[q.id] === o && s.optSelected]} onPress={() => setExamAnswers(p => ({ ...p, [q.id]: o }))}>
                      <Text style={[s.optText, examAnswers[q.id] === o && { color: T.neon1 }]}>{o}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              ))}
              <TouchableOpacity style={s.genWrap} onPress={() => Alert.alert('Soumettre ?', 'Tu vas soumettre ton examen.', [{ text: 'Annuler' }, { text: 'Soumettre', onPress: submitExam }])}>
                <LinearGradient colors={['#4A1A1A', '#E53E3E']} style={s.genBtn}>
                  {loading ? <ActivityIndicator color="#FFF" /> : <Text style={s.genBtnText}>Soumettre l'examen</Text>}
                </LinearGradient>
              </TouchableOpacity>
            </>
          )}

          {examStep === 'result' && examResult && (
            <>
              <View style={[s.caseCard, { borderColor: T.neon1 }]}>
                <Text style={[s.caseLabel, { color: T.neon1 }]}>RÉSULTAT</Text>
                <Text style={{ color: T.white, fontSize: 32, fontWeight: '900', textAlign: 'center', marginVertical: 8 }}>
                  {examResult.score}/20
                </Text>
                <Text style={s.caseText}>{examResult.feedback || `${examResult.correct} bonnes réponses sur ${examResult.total}.`}</Text>
              </View>
              {xpEarned && <Text style={s.xpInline}>+{xpEarned} XP gagnés !</Text>}
              <ActionRow onShare={() => shareResult(`Examen blanc : ${examResult.score}/20`)} onBack={backToDash} />
            </>
          )}
        </ScrollView>
        <XPNotif />
      </View>
    );
  }

  // ─── Révision mixte ────────────────────────────────────────────────────────
  if (view === 'interleaved') {
    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll}>
          <BackBtn onPress={backToDash} />
          <Text style={s.modeTitle}>🔀 Révision Mixte</Text>

          {!mixResult && (
            <>
              <Text style={s.secLabel}>SÉLECTIONNE 2-5 BRANCHES</Text>
              <Text style={[s.muted, { marginHorizontal: 16, marginBottom: 8 }]}>L'interleaving mélange les branches pour +50% de rétention</Text>
              <View style={s.branchGrid}>
                {BRANCHES.map(b => (
                  <TouchableOpacity key={b} style={[s.branchChip, mixBranches.includes(b) && s.branchActive]} onPress={() => toggleMixBranch(b)}>
                    <Text style={[s.branchText, mixBranches.includes(b) && s.branchTextActive]}>{b}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              {error && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {error}</Text></View>}
              <TouchableOpacity style={s.genWrap} onPress={startInterleaved} disabled={loading || mixBranches.length < 2}>
                <LinearGradient colors={['#1A1A4A', '#6366F1']} style={[s.genBtn, (loading || mixBranches.length < 2) && { opacity: 0.5 }]}>
                  {loading ? <ActivityIndicator color="#FFF" /> : <Text style={s.genBtnText}>🔀 Mélanger et réviser</Text>}
                </LinearGradient>
              </TouchableOpacity>
            </>
          )}

          {mixResult && !mixCorrections && (
            <>
              {mixResult.questions?.map((q, i) => (
                <View key={q.id || i} style={s.quizCard}>
                  <Text style={[s.muted, { fontSize: 11, marginBottom: 4 }]}>{q.branch}</Text>
                  <Text style={s.quizQ}>{i + 1}. {q.question}</Text>
                  {q.options?.map(o => (
                    <TouchableOpacity key={o} style={[s.optBtn, mixAnswers[q.id] === o && s.optSelected]} onPress={() => setMixAnswers(p => ({ ...p, [q.id]: o }))}>
                      <Text style={[s.optText, mixAnswers[q.id] === o && { color: T.neon1 }]}>{o}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              ))}
              <TouchableOpacity style={s.genWrap} onPress={submitInterleaved}>
                <LinearGradient colors={['#1A1A4A', '#6366F1']} style={s.genBtn}>
                  <Text style={s.genBtnText}>Vérifier les réponses</Text>
                </LinearGradient>
              </TouchableOpacity>
            </>
          )}

          {mixResult && mixCorrections && (
            <>
              {mixResult.questions?.map((q, i) => {
                const ok = mixAnswers[q.id] === q.correct;
                return (
                  <View key={q.id || i} style={[s.quizCard, { borderColor: ok ? T.neon1 : T.neon3 }]}>
                    <Text style={[s.muted, { fontSize: 11 }]}>{q.branch}</Text>
                    <Text style={s.quizQ}>{i + 1}. {q.question}</Text>
                    <Text style={{ color: ok ? T.neon1 : T.neon3, fontSize: 13, marginTop: 4 }}>{ok ? '✓ Correct' : `✗ Bonne réponse : ${q.correct}`}</Text>
                    {q.explanation && <Text style={{ color: T.muted, fontSize: 12, marginTop: 4 }}>{q.explanation}</Text>}
                  </View>
                );
              })}
              {xpEarned && <Text style={s.xpInline}>+{xpEarned} XP gagnés !</Text>}
              <ActionRow onShare={() => shareResult('Révision mixte terminée')} onBack={backToDash} />
            </>
          )}
        </ScrollView>
        <XPNotif />
      </View>
    );
  }

  // ─── Rappel libre ──────────────────────────────────────────────────────────
  if (view === 'free_recall') {
    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
          <BackBtn onPress={backToDash} />
          <Text style={s.modeTitle}>✍️ Rappel Libre</Text>
          <Text style={[s.muted, { marginHorizontal: 16, marginBottom: 16 }]}>Active recall : ×2 rétention vs QCM. Tu réponds sans choix multiples.</Text>

          {recallStep === 'config' && (
            <>
              <Text style={s.secLabel}>BRANCHE DU DROIT</Text>
              <View style={s.branchGrid}>
                {BRANCHES.map(b => (
                  <TouchableOpacity key={b} style={[s.branchChip, branch === b && s.branchActive]} onPress={() => setBranch(b)}>
                    <Text style={[s.branchText, branch === b && s.branchTextActive]}>{b}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              {error && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {error}</Text></View>}
              <TouchableOpacity style={s.genWrap} onPress={startFreeRecall} disabled={loading || !branch}>
                <LinearGradient colors={['#2D1A4A', '#A855F7']} style={[s.genBtn, (!branch || loading) && { opacity: 0.5 }]}>
                  {loading ? <ActivityIndicator color="#FFF" /> : <Text style={s.genBtnText}>✍️ Générer la question</Text>}
                </LinearGradient>
              </TouchableOpacity>
            </>
          )}

          {recallStep === 'writing' && recallQuestion && (
            <>
              <View style={s.caseCard}>
                <Text style={[s.caseLabel, { color: T.neon2 }]}>QUESTION</Text>
                <Text style={s.caseText}>{recallQuestion.question}</Text>
                {recallQuestion.context && <Text style={[s.caseText, { color: T.muted, marginTop: 8, fontSize: 12 }]}>{recallQuestion.context}</Text>}
              </View>
              <Text style={s.inputLabel}>Ta réponse libre</Text>
              <TextInput
                style={[s.input, { height: 140, textAlignVertical: 'top' }]}
                multiline placeholder="Écris ta réponse sans aide..."
                placeholderTextColor={T.dimmed} value={recallAnswer} onChangeText={setRecallAnswer}
              />
              {error && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {error}</Text></View>}
              <TouchableOpacity style={s.genWrap} onPress={submitFreeRecall} disabled={loading}>
                <LinearGradient colors={['#2D1A4A', '#A855F7']} style={s.genBtn}>
                  {loading ? <ActivityIndicator color="#FFF" /> : <Text style={s.genBtnText}>Soumettre</Text>}
                </LinearGradient>
              </TouchableOpacity>
            </>
          )}

          {recallStep === 'result' && recallResult && (
            <>
              <View style={[s.caseCard, { borderColor: T.neon2 }]}>
                <Text style={[s.caseLabel, { color: T.neon2 }]}>CORRECTION</Text>
                <Text style={{ color: T.white, fontSize: 28, fontWeight: '900', textAlign: 'center', marginVertical: 8 }}>{recallResult.score}/10</Text>
                <Text style={s.caseText}>{recallResult.feedback}</Text>
                {recallResult.elaboration_question && (
                  <View style={{ marginTop: 12, padding: 12, backgroundColor: T.elevated, borderRadius: 8 }}>
                    <Text style={{ color: T.neon4, fontSize: 12, fontWeight: '700', marginBottom: 4 }}>QUESTION DE RÉFLEXION</Text>
                    <Text style={{ color: T.white, fontSize: 13 }}>{recallResult.elaboration_question}</Text>
                  </View>
                )}
              </View>
              {xpEarned && <Text style={s.xpInline}>+{xpEarned} XP gagnés !</Text>}
              <ActionRow onShare={() => shareResult(`Rappel libre ${branch} : ${recallResult.score}/10`)} onBack={backToDash} />
            </>
          )}
        </ScrollView>
        <XPNotif />
      </View>
    );
  }

  // ════════════════════════════════════════════════════════════════════════════
  //  DASHBOARD principal
  // ════════════════════════════════════════════════════════════════════════════
  const totalXP = dash?.total_xp || 0;
  const level = dash?.level || 1;
  const streak = dash?.streak_count || 0;
  const xpInLevel = totalXP % XP_PER_LEVEL;
  const earnedIds = (badges?.earned_ids || []);

  return (
    <View style={s.root}>
      <ScrollView contentContainerStyle={s.scroll}>

        {/* ── Hero Header ─────────────────────────────────────────────────── */}
        <LinearGradient colors={['#0A1628', '#0D1A35', '#080B14']} style={s.hero}>
          <View style={[s.orbGlow, { top: -30, right: -20, backgroundColor: T.glow2, width: 120, height: 120 }]} />
          <View style={[s.orbGlow, { bottom: -20, left: -30, backgroundColor: T.glow1, width: 100, height: 100 }]} />
          <Text style={s.heroIcon}>🎓</Text>
          <Text style={s.heroTitle}>LEXAVO CAMPUS</Text>
          <View style={s.heroLine} />

          {/* Gamification row */}
          <View style={s.gamRow}>
            <StreakCounter count={streak} isActive={streak > 0} />
            <View style={{ alignItems: 'center' }}>
              <Text style={s.levelBadge}>Lvl {level}</Text>
            </View>
            <Text style={{ color: T.neon4, fontSize: 12, fontWeight: '700' }}>{totalXP} XP total</Text>
          </View>

          <XPBar currentXP={xpInLevel} nextLevelXP={XP_PER_LEVEL} level={level} />
        </LinearGradient>

        {/* ── Révision du jour ─────────────────────────────────────────────── */}
        {weakBranches.length > 0 && (
          <View style={s.section}>
            <Text style={s.secLabel}>RÉVISION DU JOUR</Text>
            {weakBranches.slice(0, 2).map(wb => (
              <TouchableOpacity key={wb.branch} style={s.weakCard} onPress={() => { setBranch(wb.branch); setActiveMode(MODES[0]); setView('branch_select'); }}>
                <View>
                  <Text style={s.weakTitle}>Tu as du retard en {wb.branch}</Text>
                  <Text style={s.weakSub}>Meilleur score : {wb.best_score || 0}% — Révise maintenant</Text>
                </View>
                <Text style={{ color: T.neon1, fontSize: 20 }}>→</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* ── 9 Modes ──────────────────────────────────────────────────────── */}
        <View style={s.section}>
          <Text style={s.secLabel}>TES OUTILS D'APPRENTISSAGE</Text>
          <Text style={s.secTitle}>9 modes scientifiquement prouvés</Text>
          {MODES.map(m => (
            <TouchableOpacity key={m.id} activeOpacity={m.disabled ? 1 : 0.85} onPress={() => goMode(m)}>
              <View style={[s.modeGlowWrap, { shadowColor: m.glowColor, opacity: m.disabled ? 0.6 : 1 }]}>
                <LinearGradient colors={m.gradient} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={s.modeCard}>
                  <View style={s.modeRow}>
                    <View style={s.modeIconWrap}><Text style={s.modeIcon}>{m.icon}</Text></View>
                    <View style={s.modeBadge}><Text style={s.modeBadgeText}>{m.badge}</Text></View>
                  </View>
                  <Text style={s.modeLabel}>{m.label}</Text>
                  <Text style={s.modeSub}>{m.sub}</Text>
                  <View style={s.modeArrow}><Text style={{ color: 'rgba(255,255,255,0.5)', fontSize: 20 }}>→</Text></View>
                  <View style={s.modeCornerGlow} />
                </LinearGradient>
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* ── Badges ────────────────────────────────────────────────────────── */}
        <View style={s.section}>
          <Text style={s.secLabel}>MES BADGES</Text>
          <BadgeGrid badges={badges?.available || []} earnedIds={earnedIds} />
        </View>

        {/* ── Activité récente ──────────────────────────────────────────────── */}
        {dash?.recent_activity?.length > 0 && (
          <View style={s.section}>
            <Text style={s.secLabel}>ACTIVITÉ RÉCENTE</Text>
            {dash.recent_activity.slice(0, 5).map((a, i) => (
              <View key={i} style={s.activityRow}>
                <Text style={{ fontSize: 20 }}>{MODES.find(m => m.id === a.mode)?.icon || '📚'}</Text>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={{ color: T.white, fontSize: 13, fontWeight: '600' }}>{a.branch} — {a.mode}</Text>
                  <Text style={s.muted}>{a.score}/{a.total_questions} • {a.xp_earned} XP</Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* ── Groupes ───────────────────────────────────────────────────────── */}
        <View style={s.section}>
          <View style={s.rowBetween}>
            <Text style={s.secLabel}>MES GROUPES</Text>
            <TouchableOpacity onPress={() => { setGroupModal(true); loadGroups(); }}>
              <Text style={{ color: T.neon1, fontSize: 12, fontWeight: '700' }}>Gérer →</Text>
            </TouchableOpacity>
          </View>
          {groups.length === 0 ? (
            <TouchableOpacity style={s.groupEmptyCard} onPress={() => { setGroupModal(true); setGroupTab('create'); loadGroups(); }}>
              <Text style={{ color: T.neon1, fontSize: 24 }}>👥</Text>
              <Text style={{ color: T.white, fontSize: 14, fontWeight: '700', marginTop: 8 }}>Créer un groupe d'étude</Text>
              <Text style={s.muted}>Étudie avec ta promo</Text>
            </TouchableOpacity>
          ) : groups.slice(0, 3).map(g => (
            <View key={g.id} style={s.groupRow}>
              <Text style={{ color: T.white, fontWeight: '700' }}>{g.name}</Text>
              <Text style={s.muted}>{g.member_count || 0} membres • Code : {g.code}</Text>
            </View>
          ))}
        </View>

        {/* ── Leaderboard ───────────────────────────────────────────────────── */}
        <View style={s.section}>
          <Text style={s.secLabel}>CLASSEMENT</Text>
          <View style={s.lbToggle}>
            {['global'].map(sc => (
              <TouchableOpacity key={sc} style={[s.lbTab, lbScope === sc && s.lbTabActive]} onPress={() => setLbScope(sc)}>
                <Text style={[s.lbTabText, lbScope === sc && { color: T.neon1 }]}>Global</Text>
              </TouchableOpacity>
            ))}
          </View>
          {leaderboard.slice(0, 5).map((u, i) => (
            <View key={u.user_id || i} style={[s.lbRow, u.is_me && { borderColor: T.neon1 }]}>
              <Text style={s.lbRank}>#{i + 1}</Text>
              <Text style={{ fontSize: 20, marginHorizontal: 8 }}>{['🥇', '🥈', '🥉', '4️⃣', '5️⃣'][i] || '#'}</Text>
              <View style={{ flex: 1 }}>
                <Text style={{ color: T.white, fontWeight: u.is_me ? '900' : '600', fontSize: 13 }}>{u.name || `Juriste #${u.user_id}`} {u.is_me ? '(toi)' : ''}</Text>
                <Text style={s.muted}>Niveau {u.level} • {u.total_xp} XP</Text>
              </View>
            </View>
          ))}
          {leaderboard.length === 0 && <Text style={[s.muted, { textAlign: 'center', margin: 16 }]}>Sois le premier sur le classement !</Text>}
        </View>

      </ScrollView>

      {/* ── Modal Groupes ──────────────────────────────────────────────────── */}
      <Modal visible={groupModal} animationType="slide" transparent>
        <View style={s.modalOverlay}>
          <View style={s.modalBox}>
            <View style={s.rowBetween}>
              <Text style={s.secTitle}>Groupes d'étude</Text>
              <TouchableOpacity onPress={() => setGroupModal(false)}><Text style={{ color: T.muted, fontSize: 20 }}>✕</Text></TouchableOpacity>
            </View>
            <View style={{ flexDirection: 'row', marginVertical: 12 }}>
              {['list', 'create', 'join'].map(t => (
                <TouchableOpacity key={t} style={[s.lbTab, groupTab === t && s.lbTabActive, { flex: 1 }]} onPress={() => setGroupTab(t)}>
                  <Text style={[s.lbTabText, groupTab === t && { color: T.neon1 }, { textAlign: 'center' }]}>
                    {t === 'list' ? 'Mes groupes' : t === 'create' ? 'Créer' : 'Rejoindre'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {groupTab === 'list' && (
              groups.length === 0
                ? <Text style={[s.muted, { textAlign: 'center', margin: 16 }]}>Aucun groupe pour l'instant.</Text>
                : groups.map(g => (
                  <View key={g.id} style={s.groupRow}>
                    <Text style={{ color: T.white, fontWeight: '700' }}>{g.name}</Text>
                    <Text style={s.muted}>Code : {g.code} • {g.member_count || 0} membres</Text>
                  </View>
                ))
            )}

            {groupTab === 'create' && (
              <>
                <TextInput style={s.input} placeholder="Nom du groupe (ex: Promo 2025)" placeholderTextColor={T.dimmed} value={groupName} onChangeText={setGroupName} />
                <TouchableOpacity style={s.genWrap} onPress={handleCreateGroup}>
                  <LinearGradient colors={[T.neon1, T.neon2]} style={s.genBtn}>
                    <Text style={s.genBtnText}>Créer le groupe</Text>
                  </LinearGradient>
                </TouchableOpacity>
              </>
            )}

            {groupTab === 'join' && (
              <>
                <TextInput style={s.input} placeholder="Code d'invitation (ex: LAW-25)" placeholderTextColor={T.dimmed} value={joinCode} onChangeText={setJoinCode} autoCapitalize="characters" />
                <TouchableOpacity style={s.genWrap} onPress={handleJoinGroup}>
                  <LinearGradient colors={[T.neon2, T.neon1]} style={s.genBtn}>
                    <Text style={s.genBtnText}>Rejoindre</Text>
                  </LinearGradient>
                </TouchableOpacity>
              </>
            )}
          </View>
        </View>
      </Modal>

      <XPNotif />
    </View>
  );
}

// ─── Petits composants internes ──────────────────────────────────────────────
const BackBtn = ({ onPress }) => (
  <TouchableOpacity activeOpacity={0.75} onPress={onPress}>
    <Text style={{ color: T.neon1, fontSize: 14, margin: 16, fontWeight: '700' }}>← Retour au dashboard</Text>
  </TouchableOpacity>
);

const ActionRow = ({ onShare, onBack }) => (
  <View style={{ flexDirection: 'row', gap: 12, marginHorizontal: 16, marginTop: 16, marginBottom: 24 }}>
    <TouchableOpacity style={{ flex: 1 }} onPress={onShare}>
      <LinearGradient colors={[T.neon2, T.neon1]} style={[s.genBtn, { marginHorizontal: 0 }]}>
        <Text style={s.genBtnText}>Partager</Text>
      </LinearGradient>
    </TouchableOpacity>
    <TouchableOpacity style={{ flex: 1 }} onPress={onBack}>
      <View style={[s.genBtn, { marginHorizontal: 0, backgroundColor: T.elevated, borderColor: T.borderLit, borderWidth: 1 }]}>
        <Text style={[s.genBtnText, { color: T.white }]}>Dashboard</Text>
      </View>
    </TouchableOpacity>
  </View>
);

// ─── Styles ──────────────────────────────────────────────────────────────────
const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: T.bg },
  scroll: { paddingBottom: 40 },

  // Hero
  hero: { paddingTop: 60, paddingBottom: 28, paddingHorizontal: 20, alignItems: 'center', overflow: 'hidden', position: 'relative' },
  orbGlow: { position: 'absolute', borderRadius: 999 },
  heroIcon: { fontSize: 36, marginBottom: 8 },
  heroTitle: { fontSize: 24, fontWeight: '900', color: T.white, letterSpacing: 3 },
  heroLine: { width: 50, height: 2, backgroundColor: T.neon1, marginVertical: 10, borderRadius: 2 },
  gamRow: { flexDirection: 'row', alignItems: 'center', gap: 20, marginTop: 8, marginBottom: 12 },
  levelBadge: { color: T.neon2, fontSize: 16, fontWeight: '900', backgroundColor: T.elevated, paddingHorizontal: 12, paddingVertical: 4, borderRadius: 20, borderWidth: 1, borderColor: T.neon2 + '50' },

  // Section
  section: { marginTop: 24, paddingHorizontal: 16 },
  secLabel: { fontSize: 10, fontWeight: '800', color: T.muted, letterSpacing: 2, marginBottom: 8 },
  secTitle: { fontSize: 17, fontWeight: '800', color: T.white, marginBottom: 14 },
  muted: { color: T.muted, fontSize: 12 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  rowCentered: { flexDirection: 'row', justifyContent: 'center', gap: 12, marginBottom: 16 },

  // Weak branches
  weakCard: { backgroundColor: T.surface, borderRadius: 12, padding: 16, marginBottom: 8, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderWidth: 1, borderColor: T.neon4 + '40' },
  weakTitle: { color: T.white, fontSize: 14, fontWeight: '700' },
  weakSub: { color: T.muted, fontSize: 12, marginTop: 2 },

  // Mode cards
  modeGlowWrap: { marginBottom: 12, borderRadius: 16, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 1, shadowRadius: 20, elevation: 8 },
  modeCard: { borderRadius: 16, padding: 20, overflow: 'hidden', minHeight: 110 },
  modeRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  modeIconWrap: { width: 42, height: 42, borderRadius: 12, backgroundColor: 'rgba(255,255,255,0.15)', alignItems: 'center', justifyContent: 'center' },
  modeIcon: { fontSize: 20 },
  modeBadge: { backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: 20, paddingHorizontal: 10, paddingVertical: 3 },
  modeBadgeText: { color: '#FFF', fontSize: 9, fontWeight: '800', letterSpacing: 0.5 },
  modeLabel: { fontSize: 18, fontWeight: '900', color: '#FFF', letterSpacing: 0.5, marginBottom: 4 },
  modeSub: { fontSize: 12, color: 'rgba(255,255,255,0.7)', lineHeight: 17 },
  modeArrow: { position: 'absolute', bottom: 16, right: 16 },
  modeCornerGlow: { position: 'absolute', top: -30, right: -30, width: 80, height: 80, borderRadius: 40, backgroundColor: 'rgba(255,255,255,0.06)' },

  // Branch selector
  branchHeader: { padding: 16, alignItems: 'center' },
  branchBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, marginBottom: 12 },
  branchBadgeText: { color: '#FFF', fontSize: 12, fontWeight: '800' },
  branchGrid: { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: 12, gap: 8, marginBottom: 16 },
  branchChip: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20, backgroundColor: T.surface, borderWidth: 1, borderColor: T.border },
  branchActive: { backgroundColor: T.neon1 + '20', borderColor: T.neon1 },
  branchText: { color: T.muted, fontSize: 12, fontWeight: '600' },
  branchTextActive: { color: T.neon1 },

  // Difficulty chips
  diffChip: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20, backgroundColor: T.surface, borderWidth: 1, borderColor: T.border },
  diffActive: { borderColor: T.neon1, backgroundColor: T.neon1 + '20' },
  diffText: { color: T.muted, fontSize: 13, fontWeight: '600' },

  // Input
  inputWrap: { marginHorizontal: 16, marginBottom: 16 },
  inputLabel: { color: T.muted, fontSize: 11, fontWeight: '700', letterSpacing: 1, marginBottom: 6, marginHorizontal: 16 },
  input: { backgroundColor: T.surface, borderRadius: 12, borderWidth: 1, borderColor: T.borderLit, color: T.white, fontSize: 14, paddingHorizontal: 14, paddingVertical: 12, marginHorizontal: 16, marginBottom: 12 },

  // Generate button
  genWrap: { marginHorizontal: 16, marginTop: 8, marginBottom: 16 },
  genBtn: { borderRadius: 14, paddingVertical: 16, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: 8 },
  genBtnText: { color: '#FFF', fontSize: 15, fontWeight: '800', letterSpacing: 0.5 },

  // Error
  errorBox: { marginHorizontal: 16, marginBottom: 12, padding: 12, backgroundColor: T.glow3, borderRadius: 10, borderWidth: 1, borderColor: T.neon3 + '50' },
  errorText: { color: T.neon3, fontSize: 13 },

  // Back
  back: { color: T.neon1, fontSize: 14, margin: 16, fontWeight: '700' },

  // Mode title
  modeTitle: { color: T.white, fontSize: 20, fontWeight: '900', margin: 16, marginBottom: 8 },

  // Quiz
  quizCard: { backgroundColor: T.surface, borderRadius: 12, padding: 16, marginHorizontal: 16, marginBottom: 12, borderWidth: 1, borderColor: T.border },
  quizQ: { color: T.white, fontSize: 14, fontWeight: '700', marginBottom: 10, lineHeight: 20 },
  optBtn: { padding: 12, borderRadius: 10, borderWidth: 1, borderColor: T.border, marginBottom: 6, backgroundColor: T.surfaceAlt },
  optSelected: { borderColor: T.neon1, backgroundColor: T.neon1 + '15' },
  optText: { color: T.white, fontSize: 13 },

  // Flashcards
  flashCard: { marginHorizontal: 16, marginBottom: 12, borderRadius: 16, overflow: 'hidden', elevation: 4 },
  flashCardFlipped: {},
  flashCardInner: { padding: 24, minHeight: 120, justifyContent: 'center', alignItems: 'center' },
  flashLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10, fontWeight: '800', letterSpacing: 2, marginBottom: 10 },
  flashText: { color: '#FFF', fontSize: 16, fontWeight: '700', textAlign: 'center' },
  flashArticle: { color: 'rgba(255,255,255,0.7)', fontSize: 11, marginTop: 10 },

  // Summary
  summaryCard: { backgroundColor: T.surface, borderRadius: 14, padding: 18, marginHorizontal: 16, borderWidth: 1, borderColor: T.border },

  // Chat
  bubble: { marginHorizontal: 16, marginBottom: 10, padding: 14, borderRadius: 14, maxWidth: SW * 0.85 },
  bubbleAI: { backgroundColor: T.surface, alignSelf: 'flex-start', borderWidth: 1, borderColor: T.border },
  bubbleUser: { backgroundColor: T.neon2 + '30', alignSelf: 'flex-end', borderWidth: 1, borderColor: T.neon2 + '50' },
  chatBar: { flexDirection: 'row', padding: 12, paddingBottom: 28, backgroundColor: T.surface, borderTopWidth: 1, borderTopColor: T.border, gap: 8 },
  chatInput: { flex: 1, color: T.white, fontSize: 14, backgroundColor: T.elevated, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 10, maxHeight: 100 },
  chatSend: { width: 44, height: 44, borderRadius: 22, overflow: 'hidden' },
  chatSendGrad: { flex: 1, alignItems: 'center', justifyContent: 'center' },

  // Cas pratique
  caseCard: { backgroundColor: T.surface, borderRadius: 14, padding: 16, marginHorizontal: 16, marginBottom: 12, borderWidth: 1, borderColor: T.border },
  caseLabel: { color: T.muted, fontSize: 10, fontWeight: '800', letterSpacing: 2, marginBottom: 8 },
  caseText: { color: T.white, fontSize: 14, lineHeight: 21 },

  // Timer
  timerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginHorizontal: 16, marginBottom: 8, backgroundColor: T.surface, padding: 12, borderRadius: 12, borderWidth: 1, borderColor: T.border },
  timerText: { color: T.neon4, fontSize: 22, fontWeight: '900' },

  // Activity
  activityRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: T.border },

  // Groups
  groupEmptyCard: { backgroundColor: T.surface, borderRadius: 14, padding: 20, alignItems: 'center', borderWidth: 1, borderColor: T.borderLit, borderStyle: 'dashed' },
  groupRow: { backgroundColor: T.surface, borderRadius: 12, padding: 14, marginBottom: 8, borderWidth: 1, borderColor: T.border },

  // Leaderboard
  lbToggle: { flexDirection: 'row', backgroundColor: T.surface, borderRadius: 10, padding: 4, marginBottom: 12 },
  lbTab: { flex: 1, paddingVertical: 8, borderRadius: 8 },
  lbTabActive: { backgroundColor: T.elevated },
  lbTabText: { color: T.muted, fontSize: 12, fontWeight: '700', textAlign: 'center' },
  lbRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, paddingHorizontal: 12, backgroundColor: T.surface, borderRadius: 12, marginBottom: 6, borderWidth: 1, borderColor: T.border },
  lbRank: { color: T.muted, fontSize: 13, fontWeight: '800', width: 24 },

  // XP notification
  xpNotif: { position: 'absolute', bottom: 80, alignSelf: 'center', backgroundColor: T.neon1, paddingHorizontal: 20, paddingVertical: 12, borderRadius: 20, alignItems: 'center', elevation: 10 },
  xpNotifText: { color: '#000', fontSize: 22, fontWeight: '900' },
  xpNotifBadge: { color: '#000', fontSize: 14, fontWeight: '700', marginTop: 2 },
  xpNotifDismiss: { color: 'rgba(0,0,0,0.6)', fontSize: 10, marginTop: 4 },
  xpInline: { color: T.neon1, fontSize: 18, fontWeight: '900', textAlign: 'center', marginVertical: 12 },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  modalBox: { backgroundColor: T.surface, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, paddingBottom: 40, borderWidth: 1, borderColor: T.borderLit },
});

const mdStyle = {
  body: { color: T.white, fontSize: 14, lineHeight: 22 },
  heading1: { color: T.neon1, fontWeight: '800', marginBottom: 8 },
  heading2: { color: T.neon1, fontWeight: '700', marginBottom: 6 },
  strong: { color: T.white, fontWeight: '800' },
  code_inline: { backgroundColor: T.elevated, color: T.neon4, borderRadius: 4, paddingHorizontal: 4 },
  bullet_list: { marginVertical: 4 },
};
