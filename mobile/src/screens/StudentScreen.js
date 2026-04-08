/**
 * StudentScreen — Lexavo Campus v2
 * Dashboard gamifié : XP, Streak, Badges, 9 modes d'apprentissage, Groupes, Leaderboard
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform, Dimensions,
  Modal, Share, Alert, Image,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { LinearGradient } from 'expo-linear-gradient';
import {
  generateQuiz, generateFlashcards, generateSummary, askQuestion,
  getStudentDashboard, postStudentActivity, getStudentLeaderboard,
  generateCaseStudy, evaluateCaseStudy, generateMockExam, submitMockExam,
  getStudentBadges, getStudentWeakBranches, generateFreeRecall,
  evaluateFreeRecall, generateInterleavedQuiz,
  createStudentGroup, joinStudentGroup, getStudentGroups,
  getLMSStatus, getLMSUniversities, connectLMS, getLMSCourses,
  getLMSCourseContent, importLMSContent, disconnectLMS,
  shareNote, listSharedNotes, getSharedNote, likeSharedNote,
  uploadNoteFile,
} from '../api/client';
import * as DocumentPicker from 'expo-document-picker';
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
  const [view, setView] = useState('dashboard'); // 'dashboard' | 'topic_input' | mode.id
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

  // Chat (conversationnel — conversation_id persistant)
  const [messages, setMessages] = useState([{ role: 'assistant', content: 'Salut ! Je suis ton tuteur IA en droit belge.\n\nPose-moi n\'importe quelle question, ou photographie tes notes.' }]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatScrollRef = useRef(null);
  const [conversationId, setConversationId] = useState(null);

  // Notes partagées
  const [notesModal, setNotesModal] = useState(false);
  const [notesTab, setNotesTab] = useState('browse'); // browse | share | view
  const [notesList, setNotesList] = useState([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [notesSubjectFilter, setNotesSubjectFilter] = useState(null);
  const [activeNote, setActiveNote] = useState(null);
  const [shareForm, setShareForm] = useState({ title: '', subject: 'droit_civil', content: '', university: '', year: '', anonymous: true, authorName: '' });
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadedDoc, setUploadedDoc] = useState({ text: '', filename: '' }); // document importé pour génération

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

  // LMS (Moodle)
  const [lmsConnected, setLmsConnected] = useState(false);
  const [lmsSiteName, setLmsSiteName] = useState('');
  const [lmsFullname, setLmsFullname] = useState('');
  const [lmsCourses, setLmsCourses] = useState([]);
  const [lmsModal, setLmsModal] = useState(false);
  const [lmsTab, setLmsTab] = useState('connect'); // connect | courses | content
  const [lmsUrl, setLmsUrl] = useState('');
  const [lmsUser, setLmsUser] = useState('');
  const [lmsPass, setLmsPass] = useState('');
  const [lmsUniversities, setLmsUniversities] = useState([]);
  const [lmsLoading, setLmsLoading] = useState(false);
  const [lmsError, setLmsError] = useState('');
  const [lmsCourseContent, setLmsCourseContent] = useState(null);
  const [lmsActiveCourse, setLmsActiveCourse] = useState(null);

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
    setUploadedDoc({ text: '', filename: '' });
    // Tuteur IA → chat direct
    if (m.id === 'chat') { setView('chat'); return; }
    // Tous les autres modes → écran conversationnel unifié
    if (m.id === 'case_study') { setCaseStep('config'); }
    if (m.id === 'mock_exam') { setExamStep('config'); setExamBranches([]); }
    if (m.id === 'free_recall') { setRecallStep('config'); }
    if (m.id === 'interleaved') { setMixBranches([]); }
    setView('topic_input');
  };

  const backToDash = () => {
    setView('dashboard');
    setActiveMode(null); setBranch(null); setResult(null); setError(null);
    setCaseStep('config'); setExamStep('config'); setRecallStep('config');
    setExamData(null); setCaseData(null); setRecallQuestion(null);
    setMixBranches([]); setMixResult(null);
    setUploadedDoc({ text: '', filename: '' });
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
    const subject = topic.trim() || branch;
    if (!subject && photos.length === 0) { setError('Dis-moi ce que tu veux étudier ou envoie une photo.'); return; }
    const branchName = subject || 'Analyse de document';
    setBranch(branchName);
    setLoading(true); setResult(null); setError(null);
    setSelected({}); setShowCorr(false); setFlipped({});
    try {
      let data;
      const docContent = uploadedDoc.text || '';
      if (activeMode.id === 'quiz') data = await generateQuiz(branchName, 'moyen', 10, docContent);
      else if (activeMode.id === 'flashcards') data = await generateFlashcards(branchName, topic, 12, docContent);
      else data = await generateSummary(branchName, topic || branchName, docContent);
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
      const data = await askQuestion(text || 'Analyse ces notes', {
        photos, top_k: 4,
        conversation_id: conversationId, // multi-tour
      });
      // Sauvegarder le conversation_id pour les échanges suivants
      if (data.conversation_id && !conversationId) {
        setConversationId(data.conversation_id);
      }
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
      setPhotos([]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Erreur : ' + (e.response?.data?.detail || e.message) }]);
    } finally {
      setChatLoading(false);
      setTimeout(() => chatScrollRef.current?.scrollToEnd({ animated: true }), 200);
    }
  };

  // ─── Notes partagées ──────────────────────────────────────────────────────
  const loadNotes = async (subject = null) => {
    setNotesLoading(true);
    try {
      const data = await listSharedNotes(subject);
      setNotesList(data);
    } catch (_) {}
    finally { setNotesLoading(false); }
  };

  const openNote = async (noteId) => {
    try {
      const note = await getSharedNote(noteId);
      setActiveNote(note);
      setNotesTab('view');
    } catch (_) { Alert.alert('Erreur', 'Impossible de charger cette note'); }
  };

  const handlePickFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf',
               'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
               'text/plain'],
        copyToCacheDirectory: true,
      });
      if (result.canceled) return;
      const asset = result.assets[0];
      setUploadLoading(true);
      const data = await uploadNoteFile(asset.uri, asset.name, asset.mimeType || 'application/octet-stream');
      setShareForm(p => ({
        ...p,
        content: data.extracted_text,
        title: p.title || asset.name.replace(/\.[^.]+$/, ''),
      }));
      Alert.alert('Fichier importé', `${data.char_count} caractères extraits depuis "${asset.name}". Tu peux relire et modifier avant de partager.`);
    } catch (e) {
      Alert.alert('Erreur', e.message || 'Impossible d\'importer ce fichier');
    } finally {
      setUploadLoading(false);
    }
  };

  const handlePickDocForStudy = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf',
               'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
               'text/plain'],
        copyToCacheDirectory: true,
      });
      if (result.canceled) return;
      const asset = result.assets[0];
      setUploadLoading(true);
      const data = await uploadNoteFile(asset.uri, asset.name, asset.mimeType || 'application/octet-stream');
      setUploadedDoc({ text: data.extracted_text, filename: asset.name });
      if (!topic.trim()) setTopic(asset.name.replace(/\.[^.]+$/, ''));
    } catch (e) {
      Alert.alert('Erreur', e.message || 'Impossible d\'importer ce fichier');
    } finally {
      setUploadLoading(false);
    }
  };

  const handlePickPhoto = async () => {
    if (photos.length >= 3) { Alert.alert('Maximum', '3 photos maximum.'); return; }
    Alert.alert('Ajouter une photo', '', [
      { text: '📷 Appareil photo', onPress: async () => {
        const perm = await ImagePicker.requestCameraPermissionsAsync();
        if (!perm.granted) return;
        const r = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.7, base64: true });
        if (!r.canceled && r.assets?.[0]) setPhotos(p => [...p, { uri: r.assets[0].uri, base64: r.assets[0].base64 }]);
      }},
      { text: '🖼️ Galerie', onPress: async () => {
        const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!perm.granted) return;
        const r = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.7, base64: true });
        if (!r.canceled && r.assets?.[0]) setPhotos(p => [...p, { uri: r.assets[0].uri, base64: r.assets[0].base64 }]);
      }},
      { text: 'Annuler', style: 'cancel' },
    ]);
  };

  const handleShareNote = async () => {
    const { title, subject, content, university, year, anonymous, authorName } = shareForm;
    if (!title.trim() || !content.trim()) {
      Alert.alert('Champs requis', 'Titre et contenu sont obligatoires');
      return;
    }
    try {
      await shareNote({
        title: title.trim(), subject, contentText: content.trim(),
        university: university.trim() || null, studyYear: year.trim() || null,
        isAnonymous: anonymous, authorName: authorName.trim() || null,
      });
      Alert.alert('Partagé !', 'Ta note est maintenant disponible pour tous les étudiants.');
      setShareForm({ title: '', subject: 'droit_civil', content: '', university: '', year: '', anonymous: true, authorName: '' });
      setNotesTab('browse');
      loadNotes();
    } catch (e) {
      Alert.alert('Erreur', e.response?.data?.detail || 'Impossible de partager');
    }
  };

  // ─── Cas pratique ──────────────────────────────────────────────────────────
  const startCaseStudy = async () => {
    const subject = topic.trim() || branch;
    if (!subject) { setError('Dis-moi ce que tu veux étudier.'); return; }
    setBranch(subject);
    setLoading(true); setCaseData(null); setError(null);
    try {
      const d = await generateCaseStudy(subject, caseDifficulty);
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
    const subject = topic.trim() || branch;
    if (!subject) { setError('Dis-moi sur quoi tu veux être examiné.'); return; }
    setBranch(subject);
    const branches = subject.split(/[,;+]/).map(s => s.trim()).filter(Boolean);
    setLoading(true); setExamData(null); setError(null); setExamAnswers({});
    try {
      const d = await generateMockExam(branches, 20);
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
    const subject = topic.trim() || branch;
    if (!subject) { setError('Dis-moi ce que tu veux étudier.'); return; }
    setBranch(subject);
    setLoading(true); setRecallQuestion(null); setError(null);
    try {
      const d = await generateFreeRecall(subject, uploadedDoc.text || '');
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
    const subject = topic.trim() || branch;
    if (!subject) { setError('Dis-moi quelles branches mélanger (ex: droit pénal, droit civil).'); return; }
    setBranch(subject);
    const branches = subject.split(/[,;+]/).map(s => s.trim()).filter(Boolean);
    if (branches.length < 2) { setError('Sépare les branches par des virgules (ex: droit pénal, droit civil).'); return; }
    setLoading(true); setMixResult(null); setMixAnswers({}); setMixCorrections(false); setError(null);
    try {
      const d = await generateInterleavedQuiz(branches);
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

  // toggleMixBranch / toggleExamBranch supprimés — tout passe par topic_input

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

  // ─── LMS (Moodle) ─────────────────────────────────────────────────────────
  const loadLMSStatus = async () => {
    try {
      const s = await getLMSStatus();
      setLmsConnected(s.connected);
      if (s.connected) { setLmsSiteName(s.site_name || ''); setLmsFullname(s.user_fullname || ''); }
    } catch (_) {}
  };

  const loadLMSCourses = async () => {
    setLmsLoading(true); setLmsError('');
    try {
      const d = await getLMSCourses();
      setLmsCourses(d?.courses || []);
      setLmsTab('courses');
    } catch (e) { setLmsError(e.response?.data?.detail || e.message); }
    finally { setLmsLoading(false); }
  };

  const handleLMSConnect = async () => {
    if (!lmsUrl.trim() || !lmsUser.trim() || !lmsPass) { setLmsError('Remplis tous les champs'); return; }
    setLmsLoading(true); setLmsError('');
    try {
      const r = await connectLMS(lmsUrl.trim(), lmsUser.trim(), lmsPass);
      setLmsConnected(true);
      setLmsSiteName(r.site_name || '');
      setLmsFullname(r.user_fullname || '');
      setLmsPass(''); // Ne pas garder le mot de passe
      Alert.alert('Connecté !', `${r.site_name}\n${r.user_fullname}`);
      loadLMSCourses();
    } catch (e) { setLmsError(e.response?.data?.detail || e.message || 'Échec de connexion'); }
    finally { setLmsLoading(false); }
  };

  const handleLMSDisconnect = async () => {
    Alert.alert('Déconnexion', 'Tu perdras l\'accès à tes cours importés.', [
      { text: 'Annuler' },
      { text: 'Déconnecter', style: 'destructive', onPress: async () => {
        try {
          await disconnectLMS();
          setLmsConnected(false); setLmsCourses([]); setLmsSiteName(''); setLmsFullname('');
          setLmsTab('connect');
        } catch (_) {}
      }},
    ]);
  };

  const openCourseContent = async (course) => {
    setLmsActiveCourse(course);
    setLmsLoading(true); setLmsError('');
    try {
      const d = await getLMSCourseContent(course.id);
      setLmsCourseContent(d?.sections || []);
      setLmsTab('content');
    } catch (e) { setLmsError(e.response?.data?.detail || e.message); }
    finally { setLmsLoading(false); }
  };

  const handleImportFile = async (fileUrl, courseName, courseId) => {
    setLmsLoading(true); setLmsError('');
    try {
      const r = await importLMSContent(fileUrl, courseId, courseName);
      Alert.alert('Importé !', `${r.content_length} caractères extraits.\nCe contenu sera utilisé pour tes quiz et flashcards.`);
    } catch (e) { setLmsError(e.response?.data?.detail || e.message); }
    finally { setLmsLoading(false); }
  };

  // Charger le statut LMS au montage
  useEffect(() => { loadLMSStatus(); }, []);

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

  // ─── Écran conversationnel unifié (remplace la grille de branches) ─────────
  if (view === 'topic_input') {
    // Déterminer le bouton CTA selon le mode
    const ctaLabels = {
      quiz: '⚡ Lancer le quiz', flashcards: '🃏 Générer les cartes', summary: '🚀 Synthétiser',
      case_study: '🧠 Générer un cas', mock_exam: '📝 Lancer l\'examen', free_recall: '✍️ Générer la question',
      interleaved: '🔀 Mélanger et réviser',
    };
    const ctaAction = {
      quiz: generate, flashcards: generate, summary: generate,
      case_study: startCaseStudy, mock_exam: startMockExam, free_recall: startFreeRecall,
      interleaved: startInterleaved,
    };
    const placeholder = activeMode?.id === 'interleaved'
      ? 'Ex: droit pénal, droit civil, droit du travail'
      : activeMode?.id === 'mock_exam'
      ? 'Ex: droit pénal, droit fiscal (sépare par des virgules)'
      : 'Ex: droit du travail, licenciement, contrat de bail...';

    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
          <BackBtn onPress={backToDash} />

          {/* Mode badge */}
          <View style={s.branchHeader}>
            <LinearGradient colors={activeMode?.gradient || [T.neon1, T.neon2]} style={s.branchBadge}>
              <Text style={{ fontSize: 16 }}>{activeMode?.icon}</Text>
              <Text style={s.branchBadgeText}>{activeMode?.label}</Text>
            </LinearGradient>
          </View>

          {/* Input style ChatGPT — texte + pièces jointes unifiés */}
          <View style={{ marginHorizontal: 16, marginBottom: 16 }}>
            <Text style={s.inputLabel}>Qu'est-ce que tu veux étudier ?</Text>
            <View style={{ backgroundColor: T.surface, borderRadius: 16, borderWidth: 1, borderColor: T.borderLit, overflow: 'hidden' }}>
              {/* Zone texte */}
              <TextInput
                style={{ color: T.white, fontSize: 15, paddingHorizontal: 16, paddingTop: 14, paddingBottom: 8, minHeight: 80 }}
                placeholder={placeholder}
                placeholderTextColor={T.dimmed}
                value={topic}
                onChangeText={(t) => { setTopic(t); setBranch(t); }}
                multiline
                autoFocus
              />

              {/* Aperçu pièces jointes */}
              {(uploadedDoc.filename || photos.length > 0) && (
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ paddingHorizontal: 12, paddingBottom: 8 }}>
                  {/* Chip fichier */}
                  {uploadedDoc.filename && (
                    <View style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: T.neon1 + '20', borderRadius: 8, borderWidth: 1, borderColor: T.neon1 + '50', paddingHorizontal: 10, paddingVertical: 5, marginRight: 8 }}>
                      <Text style={{ color: T.neon1, fontSize: 12, fontWeight: '600', maxWidth: 150 }} numberOfLines={1}>📄 {uploadedDoc.filename}</Text>
                      <TouchableOpacity onPress={() => setUploadedDoc({ text: '', filename: '' })} style={{ marginLeft: 6 }}>
                        <Text style={{ color: T.neon1, fontSize: 12, fontWeight: '700' }}>✕</Text>
                      </TouchableOpacity>
                    </View>
                  )}
                  {/* Thumbnails photos */}
                  {photos.map((ph, i) => (
                    <View key={i} style={{ position: 'relative', marginRight: 8 }}>
                      <Image source={{ uri: ph.uri }} style={{ width: 48, height: 48, borderRadius: 8 }} />
                      <TouchableOpacity onPress={() => setPhotos(p => p.filter((_, j) => j !== i))}
                        style={{ position: 'absolute', top: -5, right: -5, backgroundColor: T.neon3, borderRadius: 8, width: 16, height: 16, alignItems: 'center', justifyContent: 'center' }}>
                        <Text style={{ color: '#fff', fontSize: 9, fontWeight: '700' }}>✕</Text>
                      </TouchableOpacity>
                    </View>
                  ))}
                </ScrollView>
              )}

              {/* Barre d'actions */}
              <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingBottom: 10, paddingTop: 4, borderTopWidth: 1, borderTopColor: T.border, gap: 4 }}>
                {/* Bouton fichier */}
                <TouchableOpacity
                  onPress={handlePickDocForStudy}
                  disabled={uploadLoading}
                  style={{ flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: uploadedDoc.text ? T.neon1 + '20' : T.elevated, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6 }}
                >
                  {uploadLoading
                    ? <ActivityIndicator color={T.neon2} size="small" style={{ width: 16, height: 16 }} />
                    : <Text style={{ fontSize: 14 }}>📎</Text>
                  }
                  <Text style={{ color: uploadedDoc.text ? T.neon1 : T.muted, fontSize: 12, fontWeight: '600' }}>
                    {uploadedDoc.text ? 'Fichier chargé' : 'Fichier'}
                  </Text>
                </TouchableOpacity>

                {/* Bouton photo */}
                <TouchableOpacity
                  onPress={handlePickPhoto}
                  style={{ flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: photos.length > 0 ? T.neon4 + '20' : T.elevated, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6 }}
                >
                  <Text style={{ fontSize: 14 }}>📷</Text>
                  <Text style={{ color: photos.length > 0 ? T.neon4 : T.muted, fontSize: 12, fontWeight: '600' }}>
                    {photos.length > 0 ? `${photos.length} photo${photos.length > 1 ? 's' : ''}` : 'Photo'}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>

          {/* Difficulté pour cas pratique */}
          {activeMode?.id === 'case_study' && (
            <View style={{ paddingHorizontal: 16, marginTop: 12 }}>
              <Text style={s.secLabel}>DIFFICULTÉ</Text>
              <View style={s.rowCentered}>
                {['facile', 'moyen', 'difficile'].map(d => (
                  <TouchableOpacity key={d} style={[s.diffChip, caseDifficulty === d && s.diffActive]} onPress={() => setCaseDifficulty(d)}>
                    <Text style={[s.diffText, caseDifficulty === d && { color: T.neon1 }]}>{d}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          )}

          {error && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {error}</Text></View>}

          <TouchableOpacity activeOpacity={0.85} style={s.genWrap} onPress={ctaAction[activeMode?.id] || generate} disabled={loading}>
            <LinearGradient colors={activeMode?.gradient || [T.neon1, T.neon2]} style={[s.genBtn, (!topic.trim() && photos.length === 0 && !uploadedDoc.text) && { opacity: 0.5 }]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}>
              {loading ? <ActivityIndicator color="#FFF" /> : (
                <Text style={s.genBtnText}>{ctaLabels[activeMode?.id] || 'Générer'}</Text>
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

  // ─── Cas pratique (config passe par topic_input, ici on gère writing+result) ─
  if (view === 'case_study') {
    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
          <BackBtn onPress={backToDash} />
          <Text style={s.modeTitle}>🧠 Cas Pratique — {branch}</Text>

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

  // ─── Examen blanc (config passe par topic_input, ici exam+result) ─────────
  if (view === 'mock_exam') {
    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll}>
          {examStep !== 'exam' && <BackBtn onPress={backToDash} />}
          <Text style={s.modeTitle}>📝 Examen Blanc — {branch}</Text>

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

  // ─── Révision mixte (config passe par topic_input, ici quiz+corrections) ──
  if (view === 'interleaved') {
    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll}>
          <BackBtn onPress={backToDash} />
          <Text style={s.modeTitle}>🔀 Révision Mixte — {branch}</Text>

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

  // ─── Rappel libre (config passe par topic_input, ici writing+result) ──────
  if (view === 'free_recall') {
    return (
      <View style={s.root}>
        <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
          <BackBtn onPress={backToDash} />
          <Text style={s.modeTitle}>✍️ Rappel Libre — {branch}</Text>
          <Text style={[s.muted, { marginHorizontal: 16, marginBottom: 16 }]}>Active recall : ×2 rétention vs QCM. Tu réponds sans choix multiples.</Text>

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
              <TouchableOpacity key={wb.branch} style={s.weakCard} onPress={() => { setBranch(wb.branch); setTopic(wb.branch); setActiveMode(MODES[0]); setView('topic_input'); }}>
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

        {/* ── Mes cours (LMS) ────────────────────────────────────────────── */}
        <View style={s.section}>
          <View style={s.rowBetween}>
            <Text style={s.secLabel}>MES COURS</Text>
            {lmsConnected && (
              <TouchableOpacity onPress={() => { setLmsModal(true); loadLMSCourses(); }}>
                <Text style={{ color: T.neon1, fontSize: 12, fontWeight: '700' }}>Voir tout →</Text>
              </TouchableOpacity>
            )}
          </View>
          {!lmsConnected ? (
            <TouchableOpacity style={s.lmsConnectCard} onPress={() => { setLmsModal(true); setLmsTab('connect'); getLMSUniversities().then(d => setLmsUniversities(d?.universities || [])).catch(() => {}); }}>
              <LinearGradient colors={['#1A2440', '#0F1629']} style={s.lmsConnectInner}>
                <Text style={{ fontSize: 32 }}>🎓</Text>
                <Text style={{ color: T.white, fontSize: 15, fontWeight: '800', marginTop: 8 }}>Connecter mon école</Text>
                <Text style={[s.muted, { textAlign: 'center', marginTop: 4 }]}>Importe tes cours Moodle pour générer{'\n'}des quiz et flashcards personnalisés</Text>
                <View style={[s.branchChip, { marginTop: 12, borderColor: T.neon1, backgroundColor: T.neon1 + '15' }]}>
                  <Text style={{ color: T.neon1, fontSize: 12, fontWeight: '700' }}>Connecter →</Text>
                </View>
              </LinearGradient>
            </TouchableOpacity>
          ) : (
            <>
              <View style={s.lmsStatusRow}>
                <Text style={{ color: T.neon1, fontSize: 14 }}>✓</Text>
                <View style={{ flex: 1, marginLeft: 10 }}>
                  <Text style={{ color: T.white, fontSize: 13, fontWeight: '700' }}>{lmsSiteName || 'Moodle'}</Text>
                  <Text style={s.muted}>{lmsFullname} • {lmsCourses.length} cours</Text>
                </View>
              </View>
              {lmsCourses.slice(0, 3).map(c => (
                <TouchableOpacity key={c.id} style={s.lmsCourseChip} onPress={() => { setTopic(c.name); setBranch(c.name); setActiveMode(MODES[0]); setView('topic_input'); }}>
                  <Text style={{ color: T.white, fontSize: 13, fontWeight: '600', flex: 1 }}>{c.shortname || c.name}</Text>
                  <Text style={{ color: T.neon1, fontSize: 12 }}>Réviser →</Text>
                </TouchableOpacity>
              ))}
            </>
          )}
        </View>

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

        {/* ── Notes partagées ────────────────────────────────────────────── */}
        <View style={s.section}>
          <View style={s.rowBetween}>
            <Text style={s.secLabel}>NOTES PARTAGÉES</Text>
            <TouchableOpacity onPress={() => { setNotesModal(true); setNotesTab('browse'); loadNotes(); }}>
              <Text style={{ color: T.neon1, fontSize: 12, fontWeight: '700' }}>Voir tout →</Text>
            </TouchableOpacity>
          </View>
          <TouchableOpacity
            style={[s.lmsConnectCard]}
            onPress={() => { setNotesModal(true); setNotesTab('share'); }}
          >
            <LinearGradient colors={['#1A2440', '#0F1629']} style={s.lmsConnectInner}>
              <Text style={{ fontSize: 32 }}>📚</Text>
              <Text style={{ color: T.white, fontSize: 15, fontWeight: '800', marginTop: 8 }}>Partager une note</Text>
              <Text style={[s.muted, { textAlign: 'center', marginTop: 4 }]}>
                Partage tes synthèses avec la communauté.{'\n'}Tu peux rester anonyme ou mettre ton nom.
              </Text>
              <View style={[s.branchChip, { marginTop: 12, borderColor: T.neon4, backgroundColor: T.neon4 + '15' }]}>
                <Text style={{ color: T.neon4, fontSize: 12, fontWeight: '700' }}>Partager →</Text>
              </View>
            </LinearGradient>
          </TouchableOpacity>
          {notesList.slice(0, 3).map(n => (
            <TouchableOpacity key={n.id} style={s.lmsCourseChip} onPress={() => { setNotesModal(true); openNote(n.id); }}>
              <View style={{ flex: 1 }}>
                <Text style={{ color: T.white, fontSize: 13, fontWeight: '600' }}>{n.title}</Text>
                <Text style={[s.muted, { fontSize: 10 }]}>{n.author_name} • {n.subject?.replace('droit_', '').replace('_', ' ')} • ❤️ {n.likes}</Text>
              </View>
              <Text style={{ color: T.neon4, fontSize: 12 }}>Lire →</Text>
            </TouchableOpacity>
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

      {/* ── Modal Notes Partagées ─────────────────────────────────────────── */}
      <Modal visible={notesModal} animationType="slide" transparent>
        <View style={s.modalOverlay}>
          <View style={s.modalBox}>
            <View style={s.rowBetween}>
              <Text style={s.secTitle}>📚 Notes partagées</Text>
              <TouchableOpacity onPress={() => { setNotesModal(false); setNotesTab('browse'); setActiveNote(null); }}>
                <Text style={{ color: T.muted, fontSize: 20 }}>✕</Text>
              </TouchableOpacity>
            </View>

            {/* Tabs */}
            <View style={[s.lbToggle, { marginVertical: 10 }]}>
              {[{ id: 'browse', label: 'Explorer' }, { id: 'share', label: 'Partager' }].map(tab => (
                <TouchableOpacity key={tab.id} style={[s.lbTab, notesTab === tab.id && s.lbTabActive]} onPress={() => setNotesTab(tab.id)}>
                  <Text style={[s.lbTabText, notesTab === tab.id && { color: T.neon1 }]}>{tab.label}</Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Disclaimer */}
            <View style={{ backgroundColor: T.neon4 + '15', borderRadius: 8, padding: 8, marginBottom: 10 }}>
              <Text style={{ color: T.neon4, fontSize: 10, textAlign: 'center', fontStyle: 'italic' }}>
                ⚠️ Notes d'étudiants — vérifiez toujours avec vos sources officielles
              </Text>
            </View>

            <ScrollView style={{ maxHeight: 500 }}>
              {/* ── TAB: EXPLORER ── */}
              {notesTab === 'browse' && (
                <>
                  {/* Filtres matière */}
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 10 }}>
                    <TouchableOpacity style={[s.branchChip, !notesSubjectFilter && { borderColor: T.neon1, backgroundColor: T.neon1 + '15' }]} onPress={() => { setNotesSubjectFilter(null); loadNotes(); }}>
                      <Text style={{ color: !notesSubjectFilter ? T.neon1 : T.muted, fontSize: 11, fontWeight: '700' }}>Tout</Text>
                    </TouchableOpacity>
                    {['droit_penal', 'droit_civil', 'droit_constitutionnel', 'droit_commercial', 'droit_travail', 'droit_fiscal'].map(subj => (
                      <TouchableOpacity key={subj} style={[s.branchChip, notesSubjectFilter === subj && { borderColor: T.neon1, backgroundColor: T.neon1 + '15' }]}
                        onPress={() => { setNotesSubjectFilter(subj); loadNotes(subj); }}>
                        <Text style={{ color: notesSubjectFilter === subj ? T.neon1 : T.muted, fontSize: 11, fontWeight: '700' }}>{subj.replace('droit_', '').replace('_', ' ')}</Text>
                      </TouchableOpacity>
                    ))}
                  </ScrollView>

                  {notesLoading && <ActivityIndicator color={T.neon1} style={{ margin: 20 }} />}

                  {!notesLoading && notesList.length === 0 && (
                    <Text style={[s.muted, { textAlign: 'center', marginTop: 20 }]}>Aucune note partagée pour le moment. Sois le premier !</Text>
                  )}

                  {notesList.map(n => (
                    <TouchableOpacity key={n.id} style={[s.lmsCourseChip, { marginBottom: 8 }]} onPress={() => openNote(n.id)}>
                      <View style={{ flex: 1 }}>
                        <Text style={{ color: T.white, fontSize: 13, fontWeight: '700' }}>{n.title}</Text>
                        <Text style={[s.muted, { fontSize: 10, marginTop: 2 }]}>
                          {n.author_name} {n.university ? `• ${n.university}` : ''} {n.study_year ? `• ${n.study_year}` : ''}
                        </Text>
                        <Text style={[s.muted, { fontSize: 10 }]}>
                          {n.subject?.replace('droit_', '').replace('_', ' ')} • ❤️ {n.likes} • 📥 {n.downloads}
                        </Text>
                      </View>
                      <Text style={{ color: T.neon4, fontSize: 12 }}>Lire →</Text>
                    </TouchableOpacity>
                  ))}
                </>
              )}

              {/* ── TAB: VUE NOTE ── */}
              {notesTab === 'view' && activeNote && (
                <>
                  <TouchableOpacity onPress={() => { setNotesTab('browse'); setActiveNote(null); }} style={{ marginBottom: 10 }}>
                    <Text style={{ color: T.neon1, fontWeight: '700' }}>← Retour</Text>
                  </TouchableOpacity>
                  <Text style={{ color: T.white, fontSize: 17, fontWeight: '900', marginBottom: 4 }}>{activeNote.title}</Text>
                  <Text style={[s.muted, { marginBottom: 12, fontSize: 11 }]}>
                    {activeNote.author_name} {activeNote.university ? `• ${activeNote.university}` : ''} {activeNote.study_year ? `• ${activeNote.study_year}` : ''}
                    {'\n'}{activeNote.subject?.replace('droit_', '').replace('_', ' ')} • ❤️ {activeNote.likes} • 📥 {activeNote.downloads}
                  </Text>
                  <View style={{ backgroundColor: T.surface, borderRadius: 12, padding: 14, borderWidth: 1, borderColor: T.border }}>
                    <Text style={{ color: T.white, fontSize: 13, lineHeight: 20 }}>{activeNote.content_text}</Text>
                  </View>
                  <TouchableOpacity
                    style={{ backgroundColor: T.neon3 + '20', borderRadius: 10, padding: 12, alignItems: 'center', marginTop: 12 }}
                    onPress={() => { likeSharedNote(activeNote.id); setActiveNote(prev => ({ ...prev, likes: (prev.likes || 0) + 1 })); }}
                  >
                    <Text style={{ color: T.neon3, fontWeight: '700' }}>❤️ J'aime cette note</Text>
                  </TouchableOpacity>
                </>
              )}

              {/* ── TAB: PARTAGER ── */}
              {notesTab === 'share' && (
                <>
                  <Text style={{ color: T.white, fontSize: 14, fontWeight: '700', marginBottom: 10 }}>Partager une synthèse</Text>

                  {/* Anonyme ou nommé */}
                  <View style={{ flexDirection: 'row', gap: 8, marginBottom: 12 }}>
                    <TouchableOpacity
                      style={[s.branchChip, shareForm.anonymous && { borderColor: T.neon1, backgroundColor: T.neon1 + '15' }]}
                      onPress={() => setShareForm(p => ({ ...p, anonymous: true }))}
                    >
                      <Text style={{ color: shareForm.anonymous ? T.neon1 : T.muted, fontSize: 12, fontWeight: '700' }}>🙈 Anonyme</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={[s.branchChip, !shareForm.anonymous && { borderColor: T.neon4, backgroundColor: T.neon4 + '15' }]}
                      onPress={() => setShareForm(p => ({ ...p, anonymous: false }))}
                    >
                      <Text style={{ color: !shareForm.anonymous ? T.neon4 : T.muted, fontSize: 12, fontWeight: '700' }}>✍️ Mon nom</Text>
                    </TouchableOpacity>
                  </View>

                  {!shareForm.anonymous && (
                    <TextInput style={s.noteInput} placeholder="Ton nom / pseudo" placeholderTextColor={T.muted}
                      value={shareForm.authorName} onChangeText={v => setShareForm(p => ({ ...p, authorName: v }))} />
                  )}

                  <TextInput style={s.noteInput} placeholder="Titre (ex: Synthèse Droit Pénal - Chapitre 3)" placeholderTextColor={T.muted}
                    value={shareForm.title} onChangeText={v => setShareForm(p => ({ ...p, title: v }))} />

                  {/* Sélecteur matière */}
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 10 }}>
                    {['droit_civil', 'droit_penal', 'droit_constitutionnel', 'droit_commercial', 'droit_travail', 'droit_fiscal', 'droit_familial', 'procedure_civile', 'introduction_droit', 'autre'].map(subj => (
                      <TouchableOpacity key={subj}
                        style={[s.branchChip, shareForm.subject === subj && { borderColor: T.neon2, backgroundColor: T.neon2 + '15' }]}
                        onPress={() => setShareForm(p => ({ ...p, subject: subj }))}>
                        <Text style={{ color: shareForm.subject === subj ? T.neon2 : T.muted, fontSize: 11, fontWeight: '600' }}>
                          {subj.replace('droit_', '').replace('_', ' ')}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </ScrollView>

                  <TextInput style={s.noteInput} placeholder="Université (optionnel)" placeholderTextColor={T.muted}
                    value={shareForm.university} onChangeText={v => setShareForm(p => ({ ...p, university: v }))} />

                  <TextInput style={s.noteInput} placeholder="Année (ex: BAC2, MA1)" placeholderTextColor={T.muted}
                    value={shareForm.year} onChangeText={v => setShareForm(p => ({ ...p, year: v }))} />

                  {/* Bouton import fichier */}
                  <TouchableOpacity
                    style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, borderWidth: 1.5, borderColor: T.neon2, borderRadius: 12, borderStyle: 'dashed', padding: 14, marginBottom: 10 }}
                    onPress={handlePickFile}
                    disabled={uploadLoading}
                  >
                    {uploadLoading
                      ? <ActivityIndicator color={T.neon2} size="small" />
                      : <Text style={{ color: T.neon2, fontWeight: '700', fontSize: 14 }}>📎 Importer un fichier (PDF, DOCX, TXT)</Text>
                    }
                  </TouchableOpacity>

                  <Text style={{ color: T.muted, fontSize: 11, textAlign: 'center', marginBottom: 10 }}>— ou colle ton texte directement —</Text>

                  <TextInput style={[s.noteInput, { minHeight: 150, textAlignVertical: 'top' }]} multiline
                    placeholder="Colle ta synthèse / tes notes ici..." placeholderTextColor={T.muted}
                    value={shareForm.content} onChangeText={v => setShareForm(p => ({ ...p, content: v }))} />

                  <TouchableOpacity style={{ backgroundColor: T.neon1, borderRadius: 12, padding: 14, alignItems: 'center', marginTop: 10 }} onPress={handleShareNote}>
                    <Text style={{ color: '#000', fontWeight: '800', fontSize: 15 }}>📤 Partager avec la communauté</Text>
                  </TouchableOpacity>
                </>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>

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

      {/* ── Modal LMS ──────────────────────────────────────────────────────── */}
      <Modal visible={lmsModal} animationType="slide" transparent>
        <View style={s.modalOverlay}>
          <View style={[s.modalBox, { maxHeight: '85%' }]}>
            <View style={s.rowBetween}>
              <Text style={s.secTitle}>🎓 Mon école</Text>
              <TouchableOpacity onPress={() => setLmsModal(false)}><Text style={{ color: T.muted, fontSize: 20 }}>✕</Text></TouchableOpacity>
            </View>

            <ScrollView style={{ maxHeight: 500 }} keyboardShouldPersistTaps="handled">

              {/* Connexion */}
              {lmsTab === 'connect' && !lmsConnected && (
                <>
                  <Text style={[s.muted, { marginVertical: 8 }]}>Connecte-toi à ton Moodle universitaire</Text>

                  {/* Suggestions universités */}
                  {lmsUniversities.length > 0 && (
                    <View style={{ marginBottom: 12 }}>
                      <Text style={s.secLabel}>UNIVERSITÉS BELGES</Text>
                      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                        {lmsUniversities.map(u => (
                          <TouchableOpacity key={u.url} style={[s.branchChip, lmsUrl === u.url && s.branchActive, { marginRight: 8 }]}
                            onPress={() => setLmsUrl(u.url)}>
                            <Text style={[s.branchText, lmsUrl === u.url && s.branchTextActive]}>{u.name}</Text>
                          </TouchableOpacity>
                        ))}
                      </ScrollView>
                    </View>
                  )}

                  <Text style={s.inputLabel}>URL Moodle</Text>
                  <TextInput style={s.input} placeholder="https://moodle.tonuniversite.be" placeholderTextColor={T.dimmed}
                    value={lmsUrl} onChangeText={setLmsUrl} autoCapitalize="none" keyboardType="url" />

                  <Text style={s.inputLabel}>Identifiant</Text>
                  <TextInput style={s.input} placeholder="Ton identifiant universitaire" placeholderTextColor={T.dimmed}
                    value={lmsUser} onChangeText={setLmsUser} autoCapitalize="none" />

                  <Text style={s.inputLabel}>Mot de passe</Text>
                  <TextInput style={s.input} placeholder="••••••••" placeholderTextColor={T.dimmed}
                    value={lmsPass} onChangeText={setLmsPass} secureTextEntry />

                  <Text style={[s.muted, { fontSize: 10, marginTop: 4 }]}>Ton mot de passe n'est jamais stocké. Seul un token de session est conservé.</Text>

                  {lmsError ? <View style={s.errorBox}><Text style={s.errorText}>⚠️ {lmsError}</Text></View> : null}

                  <TouchableOpacity style={s.genWrap} onPress={handleLMSConnect} disabled={lmsLoading}>
                    <LinearGradient colors={[T.neon1, T.neon2]} style={s.genBtn}>
                      {lmsLoading ? <ActivityIndicator color="#FFF" /> : <Text style={s.genBtnText}>Se connecter</Text>}
                    </LinearGradient>
                  </TouchableOpacity>
                </>
              )}

              {/* Liste des cours */}
              {lmsTab === 'courses' && lmsConnected && (
                <>
                  <View style={[s.lmsStatusRow, { marginBottom: 12 }]}>
                    <Text style={{ color: T.neon1, fontSize: 14 }}>✓</Text>
                    <View style={{ flex: 1, marginLeft: 10 }}>
                      <Text style={{ color: T.white, fontSize: 13, fontWeight: '700' }}>{lmsSiteName}</Text>
                      <Text style={s.muted}>{lmsFullname}</Text>
                    </View>
                    <TouchableOpacity onPress={handleLMSDisconnect}>
                      <Text style={{ color: T.neon3, fontSize: 11, fontWeight: '700' }}>Déconnecter</Text>
                    </TouchableOpacity>
                  </View>

                  {lmsLoading && <ActivityIndicator color={T.neon1} style={{ margin: 16 }} />}

                  {lmsCourses.map(c => (
                    <TouchableOpacity key={c.id} style={s.lmsCourseChip} onPress={() => openCourseContent(c)}>
                      <View style={{ flex: 1 }}>
                        <Text style={{ color: T.white, fontSize: 13, fontWeight: '700' }}>{c.name}</Text>
                        {c.shortname ? <Text style={s.muted}>{c.shortname}</Text> : null}
                      </View>
                      <Text style={{ color: T.neon1, fontSize: 16 }}>→</Text>
                    </TouchableOpacity>
                  ))}

                  {!lmsLoading && lmsCourses.length === 0 && (
                    <Text style={[s.muted, { textAlign: 'center', margin: 16 }]}>Aucun cours trouvé</Text>
                  )}
                </>
              )}

              {/* Contenu d'un cours */}
              {lmsTab === 'content' && lmsActiveCourse && (
                <>
                  <TouchableOpacity onPress={() => setLmsTab('courses')}>
                    <Text style={{ color: T.neon1, fontSize: 13, fontWeight: '700', marginBottom: 12 }}>← Retour aux cours</Text>
                  </TouchableOpacity>
                  <Text style={{ color: T.white, fontSize: 15, fontWeight: '800', marginBottom: 12 }}>{lmsActiveCourse.name}</Text>

                  {lmsLoading && <ActivityIndicator color={T.neon1} style={{ margin: 16 }} />}

                  {lmsCourseContent?.map((sec, si) => (
                    <View key={sec.id || si} style={{ marginBottom: 16 }}>
                      {sec.name ? <Text style={[s.secLabel, { color: T.neon4 }]}>{sec.name}</Text> : null}
                      {sec.modules?.map((mod, mi) => (
                        <View key={mod.id || mi} style={s.lmsModuleRow}>
                          <Text style={{ color: T.white, fontSize: 13, fontWeight: '600', flex: 1 }}>
                            {mod.type === 'resource' ? '📄' : mod.type === 'page' ? '📝' : mod.type === 'url' ? '🔗' : '📁'} {mod.name}
                          </Text>
                          {mod.contents?.map((file, fi) => (
                            <TouchableOpacity key={fi} style={s.lmsImportBtn}
                              onPress={() => handleImportFile(file.fileurl, lmsActiveCourse.name, lmsActiveCourse.id)}>
                              <Text style={{ color: T.neon1, fontSize: 11, fontWeight: '700' }}>Importer</Text>
                            </TouchableOpacity>
                          ))}
                          {!mod.contents?.length && mod.description ? (
                            <TouchableOpacity style={s.lmsImportBtn}
                              onPress={() => { setTopic(mod.name); setBranch(lmsActiveCourse.name); setActiveMode(MODES[0]); setLmsModal(false); setView('topic_input'); }}>
                              <Text style={{ color: T.neon1, fontSize: 11, fontWeight: '700' }}>Réviser</Text>
                            </TouchableOpacity>
                          ) : null}
                        </View>
                      ))}
                    </View>
                  ))}

                  {!lmsLoading && (!lmsCourseContent || lmsCourseContent.length === 0) && (
                    <Text style={[s.muted, { textAlign: 'center', margin: 16 }]}>Aucun contenu disponible</Text>
                  )}

                  {/* CTA : réviser ce cours */}
                  <TouchableOpacity style={s.genWrap} onPress={() => { setTopic(lmsActiveCourse.name); setBranch(lmsActiveCourse.name); setActiveMode(MODES[0]); setLmsModal(false); setView('topic_input'); }}>
                    <LinearGradient colors={[T.neon1, T.neon2]} style={s.genBtn}>
                      <Text style={s.genBtnText}>⚡ Réviser ce cours</Text>
                    </LinearGradient>
                  </TouchableOpacity>
                </>
              )}
            </ScrollView>
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

  // LMS
  lmsConnectCard: { borderRadius: 16, overflow: 'hidden', borderWidth: 1, borderColor: T.borderLit, borderStyle: 'dashed' },
  lmsConnectInner: { padding: 24, alignItems: 'center' },
  noteInput: { backgroundColor: T.surface, borderRadius: 10, padding: 12, color: T.white, fontSize: 13, borderWidth: 1, borderColor: T.border, marginBottom: 10 },
  lmsStatusRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: T.surface, borderRadius: 12, padding: 14, borderWidth: 1, borderColor: T.neon1 + '30', marginBottom: 8 },
  lmsCourseChip: { flexDirection: 'row', alignItems: 'center', backgroundColor: T.surface, borderRadius: 12, padding: 14, marginBottom: 8, borderWidth: 1, borderColor: T.border },
  lmsModuleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 10, paddingHorizontal: 4, borderBottomWidth: 1, borderBottomColor: T.border },
  lmsImportBtn: { paddingHorizontal: 12, paddingVertical: 5, borderRadius: 8, backgroundColor: T.neon1 + '15', borderWidth: 1, borderColor: T.neon1 + '40', marginLeft: 8 },
});

const mdStyle = {
  body: { color: T.white, fontSize: 14, lineHeight: 22 },
  heading1: { color: T.neon1, fontWeight: '800', marginBottom: 8 },
  heading2: { color: T.neon1, fontWeight: '700', marginBottom: 6 },
  strong: { color: T.white, fontWeight: '800' },
  code_inline: { backgroundColor: T.elevated, color: T.neon4, borderRadius: 4, paddingHorizontal: 4 },
  bullet_list: { marginVertical: 4 },
};
