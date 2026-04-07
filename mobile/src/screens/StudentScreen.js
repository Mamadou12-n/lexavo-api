/**
 * StudentScreen — Lexavo Campus
 * Design futuriste glassmorphic — Quiz, Flashcards, Résumé, Tuteur IA, NotebookLM
 *
 * Aesthetic: Dark futuristic with neon accents, glassmorphism, glow effects
 * Typography: Bold 900 for headers, clean sans-serif for body
 * Colors: Deep space (#080B14), neon turquoise (#00D4AA), electric purple (#8B5CF6)
 */

import React, { useState, useRef } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform, Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { generateQuiz, generateFlashcards, generateSummary, askQuestion } from '../api/client';
import Markdown from 'react-native-markdown-display';
import PhotoPicker from '../components/PhotoPicker';

const { width: SW } = Dimensions.get('window');

// ─── Design System ──────────────────────────────────────────────────────────
const T = {
  // Space
  bg:        '#080B14',
  surface:   '#0F1629',
  surfaceAlt:'#141D33',
  elevated:  '#1A2440',
  // Borders
  border:    '#1E2A45',
  borderLit: '#2A3A5C',
  // Neon accents
  neon1:     '#00D4AA', // turquoise
  neon2:     '#8B5CF6', // purple
  neon3:     '#FF6B6B', // coral
  neon4:     '#FFB84D', // amber
  neon5:     '#4DA6FF', // sky blue
  // Text
  white:     '#F0F4FF',
  muted:     '#5A6B8A',
  dimmed:    '#3A4A6A',
  // Glow
  glow1:     'rgba(0, 212, 170, 0.12)',
  glow2:     'rgba(139, 92, 246, 0.12)',
  glow3:     'rgba(255, 107, 107, 0.12)',
};

const BRANCHES = [
  'Droit du travail', 'Droit familial', 'Droit fiscal', 'Droit pénal',
  'Droit civil', 'Droit administratif', 'Droit commercial', 'Droit immobilier',
  'Propriété intellectuelle', 'Sécurité sociale', 'Droit des étrangers',
  'Droit européen', 'Marchés publics', 'Environnement', 'Droits fondamentaux',
];

const MODES = [
  {
    id: 'quiz', label: 'Quiz IA',
    sub: 'L\'IA s\'adapte à ton niveau. Zéro question bateau.',
    gradient: ['#4A1D96', '#8B5CF6'],
    glowColor: 'rgba(139, 92, 246, 0.25)',
    icon: '⚡', badge: 'ADAPTATIF',
  },
  {
    id: 'flashcards', label: 'Flash Cards',
    sub: 'Swipe. Mémorise. Domine tes examens.',
    gradient: ['#004D8F', '#4DA6FF'],
    glowColor: 'rgba(77, 166, 255, 0.25)',
    icon: '✨', badge: 'INTERACTIF',
  },
  {
    id: 'summary', label: 'Résumé Turbo',
    sub: 'Des heures de cours condensées en 30 secondes.',
    gradient: ['#991B1B', '#FF6B6B'],
    glowColor: 'rgba(255, 107, 107, 0.25)',
    icon: '🚀', badge: 'ULTRA-RAPIDE',
  },
  {
    id: 'chat', label: 'Tuteur IA',
    sub: 'Ton prof particulier disponible 24/7. Pose n\'importe quelle question.',
    gradient: ['#004D40', '#00D4AA'],
    glowColor: 'rgba(0, 212, 170, 0.25)',
    icon: '🤖', badge: 'CONVERSATION',
  },
  {
    id: 'podcast', label: 'NotebookLM',
    sub: 'Révise dans le métro. L\'IA transforme tes cours en podcast.',
    gradient: ['#7C4D00', '#FFB84D'],
    glowColor: 'rgba(255, 184, 77, 0.25)',
    icon: '🎙️', badge: 'PODCAST IA',
  },
];

export default function StudentScreen() {
  const [mode, setMode]             = useState(null);
  const [branch, setBranch]         = useState(null);
  const [topic, setTopic]           = useState('');
  const [loading, setLoading]       = useState(false);
  const [result, setResult]         = useState(null);
  const [error, setError]           = useState(null);
  const [photos, setPhotos]         = useState([]);
  const [flippedCards, setFlipped]   = useState({});
  const [selectedAnswers, setSelected] = useState({});
  const [showCorrections, setShowCorr] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Salut ! Je suis ton tuteur IA en droit belge.\n\nPose-moi n\'importe quelle question, ou photographie tes notes et je les analyse instantanément.' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatScrollRef = useRef(null);

  const generate = async () => {
    if (!branch) { setError('Sélectionne une branche du droit.'); return; }
    setLoading(true); setResult(null); setError(null);
    setSelected({}); setShowCorr(false); setFlipped({});
    try {
      let data;
      if (mode === 'quiz') data = await generateQuiz(branch, 'moyen', 10);
      else if (mode === 'flashcards') data = await generateFlashcards(branch, topic, 12);
      else data = await generateSummary(branch, topic || branch);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally { setLoading(false); }
  };

  const sendChat = async () => {
    const text = chatInput.trim();
    if (!text && photos.length === 0) return;
    const userMsg = text || '[Photo envoyée pour analyse]';
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setChatInput(''); setChatLoading(true);
    try {
      const data = await askQuestion(userMsg, { photos, top_k: 4 });
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
      setPhotos([]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Erreur : ' + (e.response?.data?.detail || e.message) }]);
    } finally {
      setChatLoading(false);
      setTimeout(() => chatScrollRef.current?.scrollToEnd({ animated: true }), 200);
    }
  };

  const reset = () => {
    setResult(null); setMode(null); setBranch(null); setTopic('');
    setError(null); setSelected({}); setShowCorr(false); setFlipped({}); setPhotos([]);
  };

  const selectAnswer = (qId, a) => { if (!showCorrections) setSelected({ ...selectedAnswers, [qId]: a }); };
  const flipCard = (id) => setFlipped({ ...flippedCards, [id]: !flippedCards[id] });
  const getScore = () => {
    if (!result?.questions) return { correct: 0, total: 0 };
    let c = 0; result.questions.forEach(q => { if (selectedAnswers[q.id] === q.correct) c++; });
    return { correct: c, total: result.questions.length };
  };

  const currentMode = MODES.find(m => m.id === mode);

  return (
    <View style={s.root}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
        <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled" ref={mode === 'chat' ? chatScrollRef : undefined}>

          {/* ══════════════════════════════════════════════════════════════════
              HERO — Glassmorphic header with orbital glow
              ══════════════════════════════════════════════════════════════════ */}
          <LinearGradient colors={['#0A1628', '#0D1A35', '#080B14']} style={s.hero}>
            {/* Decorative orbital glows */}
            <View style={[s.orbGlow, { top: -30, right: -20, backgroundColor: T.glow2, width: 120, height: 120 }]} />
            <View style={[s.orbGlow, { bottom: -20, left: -30, backgroundColor: T.glow1, width: 100, height: 100 }]} />

            <Text style={s.heroIcon}>🧬</Text>
            <Text style={s.heroTitle}>LEXAVO CAMPUS</Text>
            <View style={s.heroLine} />
            <Text style={s.heroSub}>IA + OCR + Podcast — tes révisions réinventées</Text>

            {/* Feature pills */}
            <View style={s.heroPills}>
              {[
                { icon: '⚡', label: 'IA Adaptative', color: T.neon2 },
                { icon: '📷', label: 'OCR Intégré', color: T.neon1 },
                { icon: '🎙️', label: 'NotebookLM', color: T.neon4 },
              ].map((p, i) => (
                <View key={i} style={[s.heroPill, { borderColor: p.color + '40' }]}>
                  <Text style={{ fontSize: 11 }}>{p.icon}</Text>
                  <Text style={[s.heroPillText, { color: p.color }]}>{p.label}</Text>
                </View>
              ))}
            </View>
          </LinearGradient>

          {!result && mode !== 'chat' ? (
            <>
              {/* ════════════════════════════════════════════════════════════════
                  MODE SELECTION — Gradient cards with glow
                  ════════════════════════════════════════════════════════════════ */}
              {!mode ? (
                <View style={s.modeSection}>
                  <Text style={s.secLabel}>CHOISIS TON ARME</Text>
                  <Text style={s.secTitle}>5 outils pour dominer tes examens</Text>

                  {MODES.map((m) => (
                    <TouchableOpacity key={m.id} activeOpacity={0.85} onPress={() => setMode(m.id)}>
                      <View style={[s.modeGlowWrap, { shadowColor: m.glowColor }]}>
                        <LinearGradient
                          colors={m.gradient}
                          start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
                          style={s.modeCard}
                        >
                          {/* Top row: icon + badge */}
                          <View style={s.modeRow}>
                            <View style={s.modeIconWrap}>
                              <Text style={s.modeIcon}>{m.icon}</Text>
                            </View>
                            <View style={s.modeBadge}>
                              <Text style={s.modeBadgeText}>{m.badge}</Text>
                            </View>
                          </View>

                          {/* Content */}
                          <Text style={s.modeLabel}>{m.label}</Text>
                          <Text style={s.modeSub}>{m.sub}</Text>

                          {/* Arrow */}
                          <View style={s.modeArrow}>
                            <Text style={{ color: 'rgba(255,255,255,0.5)', fontSize: 20 }}>→</Text>
                          </View>

                          {/* Decorative corner glow */}
                          <View style={s.modeCornerGlow} />
                        </LinearGradient>
                      </View>
                    </TouchableOpacity>
                  ))}
                </View>
              ) : (
                <>
                  {/* ══════════════════════════════════════════════════════════
                      BRANCH SELECTION
                      ══════════════════════════════════════════════════════════ */}
                  <TouchableOpacity activeOpacity={0.75} onPress={() => { setMode(null); setBranch(null); }}>
                    <Text style={s.back}>← Retour</Text>
                  </TouchableOpacity>

                  <View style={s.branchHeader}>
                    <LinearGradient colors={currentMode?.gradient || [T.neon1, T.neon2]} style={s.branchBadge}>
                      <Text style={{ fontSize: 16 }}>{currentMode?.icon}</Text>
                      <Text style={s.branchBadgeText}>{currentMode?.label}</Text>
                    </LinearGradient>
                    <Text style={s.secTitle}>Choisis ta branche</Text>
                  </View>

                  <View style={s.branchGrid}>
                    {BRANCHES.map((b) => (
                      <TouchableOpacity
                        key={b} activeOpacity={0.75}
                        style={[s.branchChip, branch === b && s.branchActive]}
                        onPress={() => setBranch(b)}
                      >
                        <Text style={[s.branchText, branch === b && s.branchTextActive]}>{b}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>

                  {(mode === 'flashcards' || mode === 'summary' || mode === 'podcast') && (
                    <View style={s.inputWrap}>
                      <Text style={s.inputLabel}>Sujet précis (optionnel)</Text>
                      <TextInput
                        style={s.input}
                        placeholder="Ex: licenciement pour motif grave"
                        placeholderTextColor={T.dimmed}
                        value={topic} onChangeText={setTopic}
                        accessibilityLabel="Sujet précis"
                      />
                    </View>
                  )}

                  <View style={{ marginHorizontal: 16 }}>
                    <PhotoPicker photos={photos} onPhotosChange={setPhotos} label="📷 Photographier tes notes" />
                  </View>

                  {error && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {error}</Text></View>}

                  <TouchableOpacity activeOpacity={0.85} style={s.genWrap} onPress={generate} disabled={loading}>
                    <LinearGradient colors={currentMode?.gradient || [T.neon1, T.neon2]} style={s.genBtn} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}>
                      {loading ? <ActivityIndicator color="#FFF" /> : (
                        <Text style={s.genBtnText}>
                          {mode === 'quiz' ? '⚡ Lancer le quiz' : mode === 'flashcards' ? '✨ Générer les cartes' : mode === 'podcast' ? '🎙️ Générer le podcast' : '🚀 Synthétiser'}
                        </Text>
                      )}
                    </LinearGradient>
                  </TouchableOpacity>
                </>
              )}
            </>
          ) : mode === 'chat' ? (
            /* ══════════════════════════════════════════════════════════════════
               TUTEUR IA — Chat interface
               ══════════════════════════════════════════════════════════════════ */
            <>
              <LinearGradient colors={['#004D40', '#00D4AA']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={s.chatHero}>
                <View style={s.chatHeroGlow} />
                <View style={s.chatHeroContent}>
                  <Text style={s.chatHeroIcon}>🤖</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={s.chatHeroTitle}>Tuteur IA</Text>
                    <Text style={s.chatHeroSub}>Droit belge · Disponible 24/7</Text>
                  </View>
                  <View style={s.chatOnline}>
                    <View style={s.chatOnlineDot} />
                    <Text style={s.chatOnlineText}>En ligne</Text>
                  </View>
                </View>
              </LinearGradient>

              {messages.map((msg, i) => (
                <View key={i} style={[s.bubble, msg.role === 'user' ? s.bubbleUser : s.bubbleBot]}>
                  {msg.role === 'assistant' && <Text style={s.bubbleName}>🤖 Tuteur IA</Text>}
                  <Text style={[s.bubbleText, msg.role === 'user' && { color: '#FFF' }]}>{msg.content}</Text>
                </View>
              ))}
              {chatLoading && (
                <View style={[s.bubbleBot, { flexDirection: 'row', gap: 8 }]}>
                  <ActivityIndicator color={T.neon1} size="small" />
                  <Text style={s.bubbleText}>Analyse en cours...</Text>
                </View>
              )}

              <View style={{ marginHorizontal: 16, marginTop: 8 }}>
                <PhotoPicker photos={photos} onPhotosChange={setPhotos} label="📷 Photo de tes notes" />
              </View>

              <View style={s.chatBar}>
                <TextInput
                  style={s.chatInput}
                  placeholder="Pose ta question..."
                  placeholderTextColor={T.dimmed}
                  value={chatInput} onChangeText={setChatInput}
                  multiline accessibilityLabel="Question au tuteur"
                />
                <TouchableOpacity
                  activeOpacity={0.75}
                  disabled={chatLoading || (!chatInput.trim() && photos.length === 0)}
                  onPress={sendChat}
                >
                  <LinearGradient colors={['#004D40', '#00D4AA']} style={s.chatSendBtn}>
                    <Text style={{ color: '#FFF', fontWeight: '900', fontSize: 18 }}>↑</Text>
                  </LinearGradient>
                </TouchableOpacity>
              </View>

              <TouchableOpacity activeOpacity={0.75} style={s.backBtn} onPress={reset}>
                <Text style={s.backBtnText}>← Retour au Campus</Text>
              </TouchableOpacity>
            </>
          ) : (
            /* ══════════════════════════════════════════════════════════════════
               RÉSULTATS
               ══════════════════════════════════════════════════════════════════ */
            <>
              <TouchableOpacity activeOpacity={0.75} onPress={reset}>
                <Text style={s.back}>← Retour au Campus</Text>
              </TouchableOpacity>

              {/* QUIZ */}
              {mode === 'quiz' && result?.questions && (
                <>
                  <Text style={s.resultTitle}>⚡ Quiz — {result.branch || branch}</Text>
                  {result.questions.map((q, idx) => (
                    <View key={q.id || idx} style={s.quizCard}>
                      <Text style={s.quizQ}>{q.id}. {q.question}</Text>
                      {q.options?.map((opt) => {
                        const letter = opt.charAt(0);
                        const sel = selectedAnswers[q.id] === letter;
                        const ok = showCorrections && letter === q.correct;
                        const no = showCorrections && sel && letter !== q.correct;
                        return (
                          <TouchableOpacity key={opt} activeOpacity={0.75}
                            style={[s.quizOpt, sel && !showCorrections && s.quizOptSel, ok && s.quizOptOk, no && s.quizOptNo]}
                            onPress={() => selectAnswer(q.id, letter)}
                          >
                            <Text style={[s.quizOptText, sel && !showCorrections && { color: '#FFF' }, ok && { color: T.neon1 }, no && { color: T.neon3 }]}>{opt}</Text>
                          </TouchableOpacity>
                        );
                      })}
                      {showCorrections && q.explanation && (
                        <View style={s.explBox}><Text style={s.explText}>💡 {q.explanation}</Text></View>
                      )}
                    </View>
                  ))}
                  {!showCorrections ? (
                    <TouchableOpacity activeOpacity={0.85} onPress={() => setShowCorr(true)}>
                      <LinearGradient colors={['#4A1D96', '#8B5CF6']} style={s.genBtn}>
                        <Text style={s.genBtnText}>✅ Voir les corrections</Text>
                      </LinearGradient>
                    </TouchableOpacity>
                  ) : (
                    <LinearGradient colors={getScore().correct >= getScore().total * 0.7 ? ['#004D40', '#00D4AA'] : ['#7C2D12', '#FF6B6B']} style={s.scoreCard}>
                      <Text style={{ fontSize: 52 }}>{getScore().correct >= getScore().total * 0.7 ? '🎉' : '📖'}</Text>
                      <Text style={s.scoreNum}>{getScore().correct}/{getScore().total}</Text>
                      <Text style={s.scoreSub}>{getScore().correct >= getScore().total * 0.7 ? 'Tu gères !' : 'Continue à réviser !'}</Text>
                    </LinearGradient>
                  )}
                </>
              )}

              {/* FLASHCARDS */}
              {mode === 'flashcards' && result?.cards && (
                <>
                  <Text style={s.resultTitle}>✨ Flash Cards — {result.branch || branch}</Text>
                  {result.cards.map((card, idx) => {
                    const flipped = flippedCards[card.id || idx];
                    return (
                      <TouchableOpacity key={card.id || idx} activeOpacity={0.9} onPress={() => flipCard(card.id || idx)}>
                        <LinearGradient
                          colors={flipped ? ['#004D40', '#00D4AA'] : [T.surface, T.surfaceAlt]}
                          style={s.flashcard}
                        >
                          <Text style={s.flashLabel}>{flipped ? '✅ VERSO — tap pour retourner' : '❓ RECTO — tap pour retourner'}</Text>
                          <Text style={flipped ? s.flashBack : s.flashFront}>{flipped ? card.back : card.front}</Text>
                          {card.category && <View style={s.flashCat}><Text style={s.flashCatText}>{card.category}</Text></View>}
                        </LinearGradient>
                      </TouchableOpacity>
                    );
                  })}
                </>
              )}

              {/* RÉSUMÉ */}
              {mode === 'summary' && result?.summary && (
                <>
                  <Text style={s.resultTitle}>🚀 Résumé — {result.topic || branch}</Text>
                  <View style={s.summaryCard}><Markdown style={mdStyles}>{result.summary}</Markdown></View>
                </>
              )}

              {/* PODCAST */}
              {mode === 'podcast' && result?.summary && (
                <>
                  <LinearGradient colors={['#7C4D00', '#FFB84D']} style={s.podcastHero}>
                    <Text style={{ fontSize: 28 }}>🎙️</Text>
                    <View style={{ flex: 1 }}>
                      <Text style={s.podcastTitle}>NotebookLM Podcast</Text>
                      <Text style={s.podcastSub}>{result.topic || branch}</Text>
                    </View>
                    <View style={s.podcastBadge}><Text style={s.podcastBadgeText}>GÉNÉRÉ PAR IA</Text></View>
                  </LinearGradient>
                  <View style={s.summaryCard}><Markdown style={mdStyles}>{result.summary}</Markdown></View>
                  <View style={s.podcastNote}>
                    <Text style={s.podcastNoteText}>🎧 Bientôt : écoute audio réelle propulsée par NotebookLM</Text>
                  </View>
                </>
              )}

              {/* Disclaimer */}
              <View style={s.disclaimer}>
                <Text style={s.disclaimerText}>⚖️ Lexavo est un outil d'information juridique. Il ne remplace pas un avocat ni un conseiller juridique professionnel.</Text>
              </View>

              <TouchableOpacity activeOpacity={0.75} style={s.backBtn} onPress={reset}>
                <Text style={s.backBtnText}>🧬 Retour au Campus</Text>
              </TouchableOpacity>
            </>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

// ─── STYLES ─────────────────────────────────────────────────────────────────
const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: T.bg },
  scroll: { paddingBottom: 50 },

  // Hero
  hero: { paddingVertical: 28, paddingHorizontal: 24, alignItems: 'center', borderBottomLeftRadius: 28, borderBottomRightRadius: 28, marginBottom: 24, overflow: 'hidden', position: 'relative' },
  orbGlow: { position: 'absolute', borderRadius: 100, opacity: 0.6 },
  heroIcon: { fontSize: 44, marginBottom: 10 },
  heroTitle: { fontSize: 26, fontWeight: '900', color: T.white, letterSpacing: 3, textAlign: 'center' },
  heroLine: { width: 40, height: 3, backgroundColor: T.neon1, borderRadius: 2, marginVertical: 10 },
  heroSub: { fontSize: 13, color: T.muted, textAlign: 'center', lineHeight: 20 },
  heroPills: { flexDirection: 'row', gap: 8, marginTop: 18, flexWrap: 'wrap', justifyContent: 'center' },
  heroPill: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: 'rgba(255,255,255,0.04)', borderRadius: 20, paddingHorizontal: 10, paddingVertical: 6, borderWidth: 1 },
  heroPillText: { fontSize: 10, fontWeight: '700' },

  // Sections
  modeSection: { paddingHorizontal: 16 },
  secLabel: { fontSize: 10, fontWeight: '800', color: T.neon1, letterSpacing: 2, marginBottom: 4 },
  secTitle: { fontSize: 20, fontWeight: '900', color: T.white, marginBottom: 16 },

  // Mode cards
  modeGlowWrap: { marginBottom: 14, borderRadius: 20, shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0.6, shadowRadius: 16, elevation: 6 },
  modeCard: { borderRadius: 20, padding: 20, position: 'relative', overflow: 'hidden' },
  modeRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  modeIconWrap: { width: 44, height: 44, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.15)', alignItems: 'center', justifyContent: 'center' },
  modeIcon: { fontSize: 22 },
  modeBadge: { backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4 },
  modeBadgeText: { fontSize: 9, fontWeight: '900', color: '#FFF', letterSpacing: 1.5 },
  modeLabel: { fontSize: 20, fontWeight: '900', color: '#FFF', marginBottom: 4 },
  modeSub: { fontSize: 12, color: 'rgba(255,255,255,0.7)', lineHeight: 18 },
  modeArrow: { position: 'absolute', right: 20, bottom: 20 },
  modeCornerGlow: { position: 'absolute', top: -30, right: -30, width: 80, height: 80, borderRadius: 40, backgroundColor: 'rgba(255,255,255,0.06)' },

  // Back
  back: { fontSize: 14, color: T.neon1, fontWeight: '700', marginHorizontal: 16, marginBottom: 16 },

  // Branch
  branchHeader: { paddingHorizontal: 16, marginBottom: 16 },
  branchBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, alignSelf: 'flex-start', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 8, marginBottom: 12 },
  branchBadgeText: { fontSize: 14, fontWeight: '800', color: '#FFF' },
  branchGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginHorizontal: 16, marginBottom: 20 },
  branchChip: { paddingHorizontal: 14, paddingVertical: 10, borderRadius: 22, backgroundColor: T.surface, borderWidth: 1, borderColor: T.border },
  branchActive: { backgroundColor: T.neon1, borderColor: T.neon1 },
  branchText: { fontSize: 12, fontWeight: '600', color: T.muted },
  branchTextActive: { color: T.bg, fontWeight: '800' },

  // Input
  inputWrap: { marginHorizontal: 16, marginBottom: 14 },
  inputLabel: { fontSize: 11, fontWeight: '700', color: T.muted, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 },
  input: { backgroundColor: T.surface, borderRadius: 14, paddingHorizontal: 16, paddingVertical: 13, fontSize: 14, color: T.white, borderWidth: 1, borderColor: T.border },

  // Error
  errorBox: { marginHorizontal: 16, backgroundColor: T.glow3, borderRadius: 12, padding: 12, marginBottom: 14, borderWidth: 1, borderColor: 'rgba(255,107,107,0.3)' },
  errorText: { color: T.neon3, fontSize: 13 },

  // Generate
  genWrap: { marginHorizontal: 16, marginBottom: 20, borderRadius: 16, overflow: 'hidden' },
  genBtn: { paddingVertical: 16, alignItems: 'center', borderRadius: 16 },
  genBtnText: { color: '#FFF', fontSize: 16, fontWeight: '900', letterSpacing: 0.5 },

  // Chat
  chatHero: { marginHorizontal: 16, borderRadius: 18, padding: 18, marginBottom: 16, position: 'relative', overflow: 'hidden' },
  chatHeroGlow: { position: 'absolute', top: -20, right: -20, width: 80, height: 80, borderRadius: 40, backgroundColor: 'rgba(0,212,170,0.2)' },
  chatHeroContent: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  chatHeroIcon: { fontSize: 32 },
  chatHeroTitle: { fontSize: 18, fontWeight: '900', color: '#FFF' },
  chatHeroSub: { fontSize: 11, color: 'rgba(255,255,255,0.6)', marginTop: 2 },
  chatOnline: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  chatOnlineDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#00FF88' },
  chatOnlineText: { fontSize: 9, color: 'rgba(255,255,255,0.5)', fontWeight: '700' },

  bubble: { marginHorizontal: 16, marginBottom: 10, padding: 16, borderRadius: 18, maxWidth: '85%' },
  bubbleBot: { backgroundColor: T.surface, borderWidth: 1, borderColor: T.border, alignSelf: 'flex-start', borderBottomLeftRadius: 4 },
  bubbleUser: { backgroundColor: T.neon5, alignSelf: 'flex-end', borderBottomRightRadius: 4 },
  bubbleName: { fontSize: 10, color: T.neon1, fontWeight: '800', marginBottom: 6, letterSpacing: 0.5 },
  bubbleText: { fontSize: 13, color: T.white, lineHeight: 21 },

  chatBar: { flexDirection: 'row', alignItems: 'flex-end', marginHorizontal: 16, marginTop: 12, gap: 10 },
  chatInput: { flex: 1, backgroundColor: T.surface, borderRadius: 18, paddingHorizontal: 16, paddingVertical: 12, fontSize: 14, color: T.white, borderWidth: 1, borderColor: T.border, maxHeight: 100 },
  chatSendBtn: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },

  // Results
  resultTitle: { fontSize: 20, fontWeight: '900', color: T.white, marginHorizontal: 16, marginBottom: 16 },

  // Quiz
  quizCard: { marginHorizontal: 16, backgroundColor: T.surface, borderRadius: 16, padding: 18, marginBottom: 12, borderWidth: 1, borderColor: T.border },
  quizQ: { fontSize: 14, fontWeight: '700', color: T.white, marginBottom: 12, lineHeight: 22 },
  quizOpt: { padding: 13, borderRadius: 12, marginBottom: 7, backgroundColor: T.surfaceAlt, borderWidth: 1, borderColor: T.border },
  quizOptSel: { backgroundColor: T.neon2, borderColor: T.neon2 },
  quizOptOk: { backgroundColor: T.glow1, borderColor: T.neon1 },
  quizOptNo: { backgroundColor: T.glow3, borderColor: T.neon3 },
  quizOptText: { fontSize: 13, color: T.muted, lineHeight: 19 },
  explBox: { marginTop: 10, padding: 12, backgroundColor: T.glow2, borderRadius: 10, borderLeftWidth: 3, borderLeftColor: T.neon2 },
  explText: { fontSize: 12, color: '#C4B5FD', lineHeight: 19 },

  // Score
  scoreCard: { marginHorizontal: 16, borderRadius: 20, padding: 32, alignItems: 'center', marginBottom: 20 },
  scoreNum: { fontSize: 40, fontWeight: '900', color: '#FFF', marginTop: 8 },
  scoreSub: { fontSize: 15, color: 'rgba(255,255,255,0.7)', marginTop: 6 },

  // Flashcards
  flashcard: { marginHorizontal: 16, borderRadius: 18, padding: 24, marginBottom: 14, minHeight: 140, borderWidth: 1, borderColor: T.border },
  flashLabel: { fontSize: 9, fontWeight: '800', color: T.muted, marginBottom: 12, textTransform: 'uppercase', letterSpacing: 2 },
  flashFront: { fontSize: 16, fontWeight: '800', color: T.white, lineHeight: 24 },
  flashBack: { fontSize: 14, color: '#B0FFE0', lineHeight: 22 },
  flashCat: { position: 'absolute', top: 14, right: 14, backgroundColor: T.glow2, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10 },
  flashCatText: { fontSize: 9, fontWeight: '800', color: T.neon2 },

  // Summary
  summaryCard: { marginHorizontal: 16, backgroundColor: T.surface, borderRadius: 16, padding: 20, marginBottom: 16, borderWidth: 1, borderColor: T.border },

  // Podcast
  podcastHero: { marginHorizontal: 16, borderRadius: 18, padding: 18, flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 },
  podcastTitle: { fontSize: 16, fontWeight: '900', color: '#FFF' },
  podcastSub: { fontSize: 11, color: 'rgba(255,255,255,0.6)', marginTop: 2 },
  podcastBadge: { backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4 },
  podcastBadgeText: { fontSize: 8, fontWeight: '900', color: '#FFF', letterSpacing: 1 },
  podcastNote: { marginHorizontal: 16, backgroundColor: 'rgba(255,184,77,0.08)', borderRadius: 12, padding: 14, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(255,184,77,0.2)' },
  podcastNoteText: { fontSize: 12, color: T.neon4, textAlign: 'center', fontWeight: '600' },

  // Disclaimer
  disclaimer: { marginHorizontal: 16, padding: 12, backgroundColor: 'rgba(255,251,235,0.04)', borderRadius: 10, borderWidth: 1, borderColor: 'rgba(253,224,138,0.1)', marginBottom: 12 },
  disclaimerText: { fontSize: 10, color: T.dimmed, textAlign: 'center', fontStyle: 'italic', lineHeight: 15 },

  // Back button
  backBtn: { marginHorizontal: 16, paddingVertical: 16, alignItems: 'center', marginBottom: 16 },
  backBtnText: { color: T.neon1, fontSize: 14, fontWeight: '700' },
});

const mdStyles = {
  body: { fontSize: 14, color: T.white, lineHeight: 23 },
  heading1: { fontSize: 18, fontWeight: '900', color: T.neon1, marginBottom: 8 },
  heading2: { fontSize: 16, fontWeight: '800', color: T.neon2, marginBottom: 6 },
  heading3: { fontSize: 14, fontWeight: '700', color: T.neon4, marginBottom: 4 },
  strong: { fontWeight: '800', color: T.white },
  bullet_list: { marginLeft: 8 },
  list_item: { marginBottom: 4 },
  blockquote: { borderLeftWidth: 3, borderLeftColor: T.neon2, paddingLeft: 12, backgroundColor: T.glow2, borderRadius: 6, padding: 10, marginVertical: 8 },
  code_inline: { backgroundColor: T.surfaceAlt, color: T.neon1, paddingHorizontal: 6, borderRadius: 4, fontSize: 12 },
};
