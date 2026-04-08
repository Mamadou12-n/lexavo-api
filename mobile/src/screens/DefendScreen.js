/**
 * DefendScreen — Lexavo Defend v2
 * Flow 3 étapes : Catégorie → Checklist/Scan → Résultat + Lettre
 */

import React, { useState, useCallback } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform, Share, Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { LinearGradient } from 'expo-linear-gradient';
import { defendAnalyze, defendChecklist, scanAmende, regenerateDefendLetter, REGION_KEY } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import ChecklistStep from '../components/ChecklistStep';
import ScoreGauge from '../components/ScoreGauge';
import ExtractedCard from '../components/ExtractedCard';

// ─── Catégories ──────────────────────────────────────────────────────────────
const CATEGORY_GROUPS = [
  {
    label: '🚗 Automobile',
    items: [
      { id: 'amende',          label: 'Amende radar',    emoji: '📸', color: '#DC2626', hasChecklist: true },
      { id: 'parking_prive',   label: 'Parking privé',   emoji: '🅿️', color: '#7C3AED', hasChecklist: true },
      { id: 'garage_auto',     label: 'Garage / SAV',    emoji: '🔧', color: '#D97706', hasChecklist: true },
      { id: 'assurance_auto',  label: 'Assurance auto',  emoji: '🛡️', color: '#0284C7', hasChecklist: true },
      { id: 'controle_technique', label: 'Contrôle tech.',emoji: '✅', color: '#16A34A', hasChecklist: true },
    ],
  },
  {
    label: '🏛️ Administration',
    items: [
      { id: 'amende_admin',    label: 'Amende admin',    emoji: '🏛️', color: '#9D174D', hasChecklist: true },
      { id: 'sncb_stib',       label: 'SNCB / STIB',    emoji: '🚆', color: '#1D4ED8', hasChecklist: true },
      { id: 'recouvrement',    label: 'Recouvrement',    emoji: '💸', color: '#B45309', hasChecklist: false },
      { id: 'fiscal',          label: 'Fiscal',          emoji: '💰', color: '#374151', hasChecklist: false },
      { id: 'social',          label: 'Social',          emoji: '🏥', color: '#0F766E', hasChecklist: false },
    ],
  },
  {
    label: '⚡ Autres',
    items: [
      { id: 'consommation',    label: 'Consommation',    emoji: '🛒', color: '#C45A2D', hasChecklist: false },
      { id: 'bail',            label: 'Bail / Logement', emoji: '🏠', color: '#C45A2D', hasChecklist: false },
      { id: 'travail',         label: 'Travail',         emoji: '👷', color: '#C45A2D', hasChecklist: false },
      { id: 'huissier',        label: 'Huissier',        emoji: '📨', color: '#C45A2D', hasChecklist: false },
      { id: 'scolaire',        label: 'Scolaire',        emoji: '🎓', color: '#C45A2D', hasChecklist: false },
    ],
  },
];

// Catégories pouvant être scannées (PV / lettre physique)
const SCANNABLE = ['amende', 'parking_prive', 'amende_admin', 'sncb_stib'];

const REGIONS = [
  { id: 'bruxelles', label: '🏙️ Bruxelles' },
  { id: 'wallonie',  label: '🌿 Wallonie' },
  { id: 'flandre',   label: '🦁 Flandre' },
];

const TONES = [
  { id: 'formel',      label: '🏛️ Formel',      desc: 'Juridique et professionnel' },
  { id: 'ferme',       label: '💪 Ferme',        desc: 'Déterminé, sans agressivité' },
  { id: 'assertif',    label: '⚡ Assertif',      desc: 'Direct et percutant' },
  { id: 'conciliant',  label: '🤝 Conciliant',   desc: 'Dialogue et solution amiable' },
  { id: 'amical',      label: '😊 Amical',       desc: 'Courtois et accessible' },
];

// Questions par catégorie (copie mobile pour calcul du score temps réel)
const CHECKLIST_DEF = {
  amende:           ['signalisation','delai','donnees_correctes','conducteur','vitesse_plausible'],
  parking_prive:    ['signalisation_visible','lettre_officielle','base_legale','titulaire','double_paiement'],
  garage_auto:      ['devis_signe','depassement','garantie','facture_detaillee','consentement_supp'],
  assurance_auto:   ['delai_declaration','refus_motive','delai_reponse','exclusion_contrat','expertise_contradictoire'],
  amende_admin:     ['notification_delai','droit_defense','base_reglementaire','proportionnalite','recidive'],
  sncb_stib:        ['titre_valide','delai_regularisation','pv_regulier','tarif_applique','situation_speciale'],
  controle_technique:['motif_ecrit','defaut_grave','contre_expertise','delai_contre_visite'],
};

// Questions lisibles pour ChecklistStep
const CHECKLIST_QUESTIONS = {
  amende: [
    { id: 'signalisation',     question: 'La signalisation de vitesse était-elle clairement visible ?',             favorable_if: false, vice: 'Signalisation non conforme (AR 1/12/1975)' },
    { id: 'delai',             question: 'Avez-vous reçu l\'avis dans le délai légal (14 jours) ?',                 favorable_if: false, vice: 'Délai dépassé — prescription possible' },
    { id: 'donnees_correctes', question: 'Les données du PV sont-elles correctes (plaque, heure, lieu) ?',          favorable_if: false, vice: 'Erreur matérielle dans le PV' },
    { id: 'conducteur',        question: 'Étiez-vous le conducteur au moment des faits ?',                          favorable_if: false, vice: 'Désignation de conducteur possible' },
    { id: 'vitesse_plausible', question: 'La vitesse indiquée vous semble-t-elle correcte ?',                       favorable_if: false, vice: 'Contestation de la mesure radar' },
  ],
  parking_prive: [
    { id: 'signalisation_visible', question: 'La signalisation des conditions était-elle visible à l\'entrée ?',   favorable_if: false, vice: 'Pas de contrat formé sans signalisation' },
    { id: 'lettre_officielle',     question: 'Avez-vous reçu une vraie amende officielle (police) ?',              favorable_if: true,  vice: 'Lettre privée = réclamation civile, pas amende' },
    { id: 'base_legale',           question: 'La lettre mentionne-t-elle une base légale précise ?',               favorable_if: false, vice: 'Absence de fondement juridique' },
    { id: 'titulaire',             question: 'Êtes-vous le titulaire du véhicule ?',                               favorable_if: true,  vice: 'Transfert de données contestable' },
    { id: 'double_paiement',       question: 'Aviez-vous déjà payé ce stationnement ce jour-là ?',                 favorable_if: true,  vice: 'Double facturation' },
  ],
  garage_auto: [
    { id: 'devis_signe',         question: 'Aviez-vous signé un devis avant les réparations ?',                   favorable_if: false, vice: 'Absence de devis signé' },
    { id: 'depassement',         question: 'La facture dépasse-t-elle le devis de plus de 10% ?',                 favorable_if: true,  vice: 'Dépassement non autorisé (CDE art. 57)' },
    { id: 'garantie',            question: 'La panne est-elle réapparue moins de 6 mois après la réparation ?',   favorable_if: true,  vice: 'Garantie légale 2 ans applicable' },
    { id: 'facture_detaillee',   question: 'La facture est-elle détaillée (pièces + main d\'œuvre) ?',            favorable_if: false, vice: 'Facture non transparente' },
    { id: 'consentement_supp',   question: 'Vous a-t-on contacté avant des travaux supplémentaires ?',            favorable_if: false, vice: 'Travaux sans accord — non opposables' },
  ],
  assurance_auto: [
    { id: 'delai_declaration',   question: 'Avez-vous déclaré le sinistre dans le délai contractuel ?',           favorable_if: true,  vice: 'Vérifier si le délai est impératif' },
    { id: 'refus_motive',        question: 'L\'assureur a-t-il motivé son refus par écrit ?',                     favorable_if: false, vice: 'Motivation obligatoire (art. 87 Loi 2014)' },
    { id: 'delai_reponse',       question: 'L\'assureur a-t-il répondu dans les 30 jours ?',                      favorable_if: false, vice: 'Dépassement délai — plainte Ombudsman' },
    { id: 'exclusion_contrat',   question: 'Le refus est-il basé sur une clause d\'exclusion de votre contrat ?', favorable_if: false, vice: 'Clause potentiellement abusive' },
    { id: 'expertise_contradictoire', question: 'A-t-on proposé une expertise contradictoire ?',                  favorable_if: false, vice: 'Droit à expertise non respecté (art. 84)' },
  ],
  amende_admin: [
    { id: 'notification_delai', question: 'Avez-vous reçu la notification dans les 3 mois ?',                    favorable_if: false, vice: 'Prescription — délai dépassé' },
    { id: 'droit_defense',      question: 'A-t-on vous offert la possibilité de vous défendre avant décision ?', favorable_if: false, vice: 'Violation droits de la défense' },
    { id: 'base_reglementaire', question: 'L\'amende est-elle basée sur un règlement communal publié ?',         favorable_if: false, vice: 'Défaut de base réglementaire' },
    { id: 'proportionnalite',   question: 'Le montant vous semble-t-il disproportionné ?',                       favorable_if: true,  vice: 'Principe de proportionnalité violé' },
    { id: 'recidive',           question: 'Est-ce votre première infraction de ce type ?',                       favorable_if: true,  vice: 'Circonstances atténuantes — première infraction' },
  ],
  sncb_stib: [
    { id: 'titre_valide',          question: 'Aviez-vous un titre valide mais non présenté ?',                   favorable_if: true,  vice: 'Régularisation possible a posteriori' },
    { id: 'delai_regularisation',  question: 'L\'agent vous a-t-il informé du délai de régularisation ?',        favorable_if: false, vice: 'Information insuffisante' },
    { id: 'pv_regulier',           question: 'Le PV mentionne-t-il correctement la ligne, heure, lieu ?',        favorable_if: false, vice: 'Erreur matérielle dans le PV' },
    { id: 'tarif_applique',        question: 'Le montant correspond-il aux CGV affichées ?',                     favorable_if: false, vice: 'Tarif non conforme' },
    { id: 'situation_speciale',    question: 'Étiez-vous dans une situation exceptionnelle (panne app, urgence) ?', favorable_if: true, vice: 'Force majeure / recours en grâce' },
  ],
  controle_technique: [
    { id: 'motif_ecrit',        question: 'Le refus est-il accompagné d\'un rapport écrit détaillant chaque défaut ?', favorable_if: false, vice: 'Rapport motivé obligatoire (AR 23/12/1994)' },
    { id: 'defaut_grave',       question: 'Le défaut mentionné est-il réellement dangereux ?',                          favorable_if: false, vice: 'Refus disproportionné' },
    { id: 'contre_expertise',   question: 'A-t-on vous informé de votre droit à une contre-expertise ?',               favorable_if: false, vice: 'Droit à contre-expertise non mentionné' },
    { id: 'delai_contre_visite', question: 'Disposiez-vous d\'au moins 15 jours pour les réparations ?',               favorable_if: false, vice: 'Délai insuffisant accordé' },
  ],
};

function getCatById(id) {
  for (const g of CATEGORY_GROUPS) {
    const found = g.items.find(i => i.id === id);
    if (found) return found;
  }
  return null;
}

function computeScore(category, answers) {
  const questions = CHECKLIST_QUESTIONS[category] || [];
  if (!questions.length) return { score: 0, level: 'faible' };
  let score = 0;
  questions.forEach(q => {
    const val = answers[q.id];
    if (val !== undefined && val !== null && val === q.favorable_if) score++;
  });
  const pct = Math.round((score / questions.length) * 100);
  const level = pct >= 60 ? 'forte' : pct >= 30 ? 'moyenne' : 'faible';
  return { score: pct, level };
}

// ─── Composant principal ─────────────────────────────────────────────────────
export default function DefendScreen() {
  const [step, setStep]               = useState(1); // 1=catégorie, 2=analyse, 3=résultat
  const [categoryId, setCategoryId]   = useState(null);
  const [region, setRegion]           = useState(null);
  const [description, setDescription] = useState('');
  const [photos, setPhotos]           = useState([]);
  const [loading, setLoading]         = useState(false);
  const [scanLoading, setScanLoading] = useState(false);
  const [error, setError]             = useState(null);

  // Checklist
  const [answers, setAnswers]         = useState({});

  // Scan OCR
  const [scanResult, setScanResult]   = useState(null); // données extraites

  // Résultats
  const [result, setResult]             = useState(null);
  const [showLetter, setShowLetter]     = useState(false);
  const [letterTone, setLetterTone]     = useState('formel');
  const [letterText, setLetterText]     = useState(null); // lettre courante (peut changer)
  const [letterLoading, setLetterLoading] = useState(false);
  const [letterDesc, setLetterDesc]     = useState(''); // description conservée pour régénérer

  const cat = getCatById(categoryId);
  const { score, level } = computeScore(categoryId, answers);
  const questions = CHECKLIST_QUESTIONS[categoryId] || [];
  const canScan = SCANNABLE.includes(categoryId);

  // ── Handlers ────────────────────────────────────────────────────────────────
  const selectCategory = (id) => {
    setCategoryId(id);
    setAnswers({});
    setScanResult(null);
    setDescription('');
    setPhotos([]);
    setError(null);
    setStep(2);
  };

  const handleAnswer = (qId, val) => {
    setAnswers(prev => ({ ...prev, [qId]: val }));
  };

  const handleScanEdit = (field, value) => {
    setScanResult(prev => ({
      ...prev,
      extracted: { ...prev.extracted, [field]: value },
    }));
  };

  const handleScan = async () => {
    if (!photos.length) {
      Alert.alert('Photo requise', 'Ajoute d\'abord une photo de ton document.');
      return;
    }
    setScanLoading(true); setError(null); setScanResult(null);
    try {
      const res = await scanAmende(photos, categoryId);
      setScanResult(res);
      // Pré-remplir les réponses de la checklist
      if (res.prefill_checklist) {
        setAnswers(prev => ({ ...prev, ...res.prefill_checklist }));
      }
    } catch (e) {
      setError('Erreur lors du scan : ' + (e.response?.data?.detail || e.message));
    } finally { setScanLoading(false); }
  };

  const analyze = async () => {
    setLoading(true); setResult(null); setError(null);
    try {
      const savedRegion = region || await AsyncStorage.getItem(REGION_KEY);

      let res;
      if (cat?.hasChecklist && questions.length > 0) {
        let desc = description;
        if (scanResult?.extracted) {
          const ex = scanResult.extracted;
          desc = `Montant: ${ex.montant}€, Date: ${ex.date_infraction}, Lieu: ${ex.lieu}, Plaque: ${ex.plaque}. ${description}`;
        }
        setLetterDesc(desc);
        res = await defendChecklist(categoryId, answers, savedRegion, desc, photos, letterTone);
      } else {
        if (description.trim().length < 20) {
          setError('Décrivez votre situation en au moins 20 caractères.');
          setLoading(false); return;
        }
        setLetterDesc(description.trim());
        res = await defendAnalyze(description.trim(), categoryId, savedRegion, '', photos);
      }
      setResult(res);
      setLetterText(res.letter || res.document_text || null);
      setShowLetter(false);
      setStep(3);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally { setLoading(false); }
  };

  const handleGenerateLetter = async () => {
    setShowLetter(true);
    // Si un ton différent de 'formel' est déjà sélectionné, régénérer directement
    if (letterTone !== 'formel' || !letterText) {
      await handleRegenerateLetter(letterTone);
    }
  };

  const handleRegenerateLetter = async (tone) => {
    setLetterLoading(true);
    try {
      const vices = result?.vices_detected?.join(', ') || '';
      const legal = result?.legal_context || '';
      const data = await regenerateDefendLetter(letterDesc, vices, legal, tone);
      setLetterText(data.letter);
    } catch (e) {
      Alert.alert('Erreur', 'Impossible de régénérer la lettre.');
    } finally { setLetterLoading(false); }
  };

  const reset = () => {
    setStep(1); setCategoryId(null); setAnswers({});
    setScanResult(null); setResult(null); setError(null);
    setDescription(''); setPhotos([]);
    setLetterTone('formel'); setLetterText(null); setShowLetter(false); setLetterDesc('');
  };

  const shareResult = async () => {
    const text = letterText || result?.situation_analysis || '';
    if (!text) return;
    try { await Share.share({ message: text }); } catch (_) {}
  };

  // ════════════════════════════════════════════════════════════════════════════
  //  RENDER
  // ════════════════════════════════════════════════════════════════════════════
  return (
    <KeyboardAvoidingView style={s.root} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
      <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">

        {/* ── Header ── */}
        <LinearGradient colors={['#7C2D12', '#C45A2D']} style={s.hero}>
          <Text style={s.heroEmoji}>⚡</Text>
          <Text style={s.heroTitle}>Lexavo Defend</Text>
          <Text style={s.heroSub}>Contestez, réclamez, agissez — en 3 étapes</Text>
          {/* Steps indicator */}
          <View style={s.steps}>
            {['Catégorie', 'Analyse', 'Résultat'].map((l, i) => (
              <React.Fragment key={i}>
                <View style={[s.stepDot, step > i && s.stepDotDone, step === i + 1 && s.stepDotActive]}>
                  <Text style={[s.stepNum, (step > i || step === i + 1) && { color: '#FFF' }]}>{i + 1}</Text>
                </View>
                {i < 2 && <View style={[s.stepLine, step > i + 1 && s.stepLineDone]} />}
              </React.Fragment>
            ))}
          </View>
        </LinearGradient>

        {/* ══════════════════════════════════════════════════════════════════
            ÉTAPE 1 — CHOIX CATÉGORIE
            ══════════════════════════════════════════════════════════════════ */}
        {step === 1 && (
          <>
            <Text style={s.sectionTitle}>Quelle est votre situation ?</Text>
            {CATEGORY_GROUPS.map((group) => (
              <View key={group.label} style={s.group}>
                <Text style={s.groupLabel}>{group.label}</Text>
                <View style={s.catGrid}>
                  {group.items.map((item) => (
                    <TouchableOpacity
                      key={item.id}
                      activeOpacity={0.8}
                      style={[s.catCard, { borderColor: item.color + '30' }]}
                      onPress={() => selectCategory(item.id)}
                    >
                      <Text style={s.catEmoji}>{item.emoji}</Text>
                      <Text style={s.catLabel}>{item.label}</Text>
                      {item.hasChecklist && (
                        <View style={s.checklistBadge}>
                          <Text style={s.checklistBadgeText}>✓ Guidé</Text>
                        </View>
                      )}
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            ))}
            <View style={s.disclaimer}>
              <Text style={s.disclaimerText}>⚖️ Lexavo est un outil d'information juridique. Il ne remplace pas un avocat.</Text>
            </View>
          </>
        )}

        {/* ══════════════════════════════════════════════════════════════════
            ÉTAPE 2 — ANALYSE (CHECKLIST ou LIBRE)
            ══════════════════════════════════════════════════════════════════ */}
        {step === 2 && (
          <>
            <TouchableOpacity onPress={reset} style={s.backBtn}>
              <Text style={s.backText}>← Changer de catégorie</Text>
            </TouchableOpacity>

            {/* Badge catégorie */}
            <View style={[s.catBadge, { backgroundColor: (cat?.color || '#C45A2D') + '15', borderColor: (cat?.color || '#C45A2D') + '40' }]}>
              <Text style={s.catBadgeEmoji}>{cat?.emoji}</Text>
              <Text style={[s.catBadgeLabel, { color: cat?.color || '#C45A2D' }]}>{cat?.label}</Text>
              {cat?.hasChecklist && <Text style={s.catBadgeSub}>Analyse guidée des vices de forme</Text>}
            </View>

            {/* SCAN (si catégorie scannable) */}
            {canScan && (
              <View style={s.scanBox}>
                <Text style={s.scanTitle}>📷 Scanner votre document (optionnel)</Text>
                <Text style={s.scanSub}>Photographiez votre amende/lettre — l'IA extrait les données automatiquement</Text>
                <PhotoPicker photos={photos} onPhotosChange={setPhotos} label="Ajouter la photo" />
                {photos.length > 0 && !scanResult && (
                  <TouchableOpacity style={s.scanBtn} onPress={handleScan} disabled={scanLoading}>
                    {scanLoading
                      ? <ActivityIndicator color="#FFF" />
                      : <Text style={s.scanBtnText}>🔍 Analyser le document</Text>
                    }
                  </TouchableOpacity>
                )}
                {scanResult && (
                  <ExtractedCard
                    extracted={scanResult.extracted || {}}
                    confidence={scanResult.confidence || 0.5}
                    onEdit={handleScanEdit}
                  />
                )}
              </View>
            )}

            {/* CHECKLIST si catégorie guidée */}
            {cat?.hasChecklist && questions.length > 0 && (
              <>
                <Text style={s.sectionTitle}>Checklist des vices de forme</Text>
                <ChecklistStep
                  questions={questions}
                  answers={answers}
                  onAnswer={handleAnswer}
                  score={score}
                  level={level}
                />
              </>
            )}

            {/* DESCRIPTION LIBRE (toujours présente, optionnelle si checklist) */}
            <Text style={[s.sectionTitle, { marginTop: 8 }]}>
              {cat?.hasChecklist ? 'Détails supplémentaires (optionnel)' : 'Décrivez votre situation'}
            </Text>
            <View style={s.inputCard}>
              <TextInput
                style={s.textArea}
                multiline
                numberOfLines={5}
                placeholder={cat?.hasChecklist
                  ? 'Ajoutez des informations complémentaires...'
                  : 'Décrivez votre situation en détail (minimum 20 caractères)...'
                }
                placeholderTextColor={colors.textMuted}
                value={description}
                onChangeText={setDescription}
                textAlignVertical="top"
              />
              <Text style={s.charCount}>{description.length} caractères</Text>
            </View>

            {/* Photos si non-scannable */}
            {!canScan && <PhotoPicker photos={photos} onPhotosChange={setPhotos} />}

            {/* Région */}
            <Text style={s.sectionTitle}>Région</Text>
            <View style={s.regionRow}>
              {REGIONS.map(r => (
                <TouchableOpacity
                  key={r.id}
                  style={[s.regionChip, region === r.id && s.regionChipActive]}
                  onPress={() => setRegion(region === r.id ? null : r.id)}
                >
                  <Text style={[s.regionText, region === r.id && s.regionTextActive]}>{r.label}</Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Ton de la lettre */}
            <Text style={s.sectionTitle}>Ton de votre lettre</Text>
            <Text style={s.toneSub}>Vous pourrez changer de ton et régénérer autant de fois que vous voulez</Text>
            <View style={s.toneGrid}>
              {TONES.map(t => (
                <TouchableOpacity
                  key={t.id}
                  activeOpacity={0.8}
                  style={[s.toneChip, letterTone === t.id && s.toneChipActive]}
                  onPress={() => setLetterTone(t.id)}
                >
                  <Text style={[s.toneLabel, letterTone === t.id && s.toneLabelActive]}>{t.label}</Text>
                  <Text style={[s.toneDesc, letterTone === t.id && s.toneDescActive]}>{t.desc}</Text>
                </TouchableOpacity>
              ))}
            </View>

            {error && <View style={s.errorBox}><Text style={s.errorText}>⚠️ {error}</Text></View>}

            <TouchableOpacity
              activeOpacity={0.85}
              style={[s.analyzeBtn, loading && s.analyzeBtnDisabled]}
              onPress={analyze}
              disabled={loading}
            >
              {loading
                ? <ActivityIndicator color="#FFF" />
                : <Text style={s.analyzeBtnText}>🔍 Analyser ma situation</Text>
              }
            </TouchableOpacity>
          </>
        )}

        {/* ══════════════════════════════════════════════════════════════════
            ÉTAPE 3 — RÉSULTATS
            ══════════════════════════════════════════════════════════════════ */}
        {step === 3 && result && (
          <>
            <TouchableOpacity onPress={() => setStep(2)} style={s.backBtn}>
              <Text style={s.backText}>← Modifier mes réponses</Text>
            </TouchableOpacity>

            {/* ── BLOC 1 : ANALYSE COMPLÈTE ── */}

            {/* Score de contestabilité */}
            {result.contestability_score !== undefined && (
              <ScoreGauge score={result.contestability_score} level={result.contestability_level} />
            )}

            {/* Probabilité de succès (flow libre) */}
            {result.success_probability && !result.contestability_score && (
              <View style={[s.resultCard, { borderLeftWidth: 4, borderLeftColor: result.success_probability === 'elevee' ? '#10B981' : result.success_probability === 'moyenne' ? '#F59E0B' : '#EF4444' }]}>
                <Text style={s.resultTitle}>📊 Probabilité de succès</Text>
                <Text style={[s.resultText, { fontWeight: '700', fontSize: 16 }]}>
                  {result.success_probability === 'elevee' ? '🟢 Élevée' : result.success_probability === 'moyenne' ? '🟠 Moyenne' : '🔴 Faible'}
                </Text>
              </View>
            )}

            {/* Recommandation */}
            {result.recommendation && (
              <View style={s.recCard}>
                <Text style={s.recText}>{result.recommendation}</Text>
              </View>
            )}

            {/* Analyse situation détaillée */}
            {result.situation_analysis && (
              <View style={s.resultCard}>
                <Text style={s.resultTitle}>📋 Analyse de votre situation</Text>
                <Text style={s.resultText}>{result.situation_analysis}</Text>
              </View>
            )}

            {/* Vices de forme détectés */}
            {result.vices_detected?.length > 0 && (
              <View style={s.resultCard}>
                <Text style={s.resultTitle}>🎯 Vices de forme détectés</Text>
                {result.vices_detected.map((v, i) => (
                  <View key={i} style={s.viceRow}>
                    <Text style={s.viceBullet}>✓</Text>
                    <Text style={s.viceText}>{v}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Contexte juridique */}
            {result.legal_context && (
              <View style={s.legalBox}>
                <Text style={s.legalTitle}>⚖️ Contexte juridique</Text>
                <Text style={s.legalText}>{result.legal_context}</Text>
              </View>
            )}

            {/* Prochaines étapes */}
            {result.next_steps?.length > 0 && (
              <View style={s.resultCard}>
                <Text style={s.resultTitle}>📌 Prochaines étapes</Text>
                {result.next_steps.map((st, i) => (
                  <View key={i} style={s.stepRow}>
                    <View style={s.stepNum2}><Text style={s.stepNumText}>{i + 1}</Text></View>
                    <Text style={s.stepText}>{st}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* ── SÉPARATEUR ── */}
            <View style={s.letterSeparator}>
              <View style={s.letterSepLine} />
              <Text style={s.letterSepText}>Passer à l'action</Text>
              <View style={s.letterSepLine} />
            </View>

            {/* ── SÉLECTEUR DE TON (toujours visible dans step 3) ── */}
            {(result.letter || result.document_text) && (
              <>
                <Text style={s.sectionTitle}>Choisissez le ton de votre lettre</Text>
                <View style={s.toneGrid}>
                  {TONES.map(t => (
                    <TouchableOpacity
                      key={t.id}
                      activeOpacity={0.8}
                      style={[s.toneChip, letterTone === t.id && s.toneChipActive]}
                      onPress={() => setLetterTone(t.id)}
                    >
                      <Text style={[s.toneLabel, letterTone === t.id && s.toneLabelActive]}>{t.label}</Text>
                      <Text style={[s.toneDesc, letterTone === t.id && s.toneDescActive]}>{t.desc}</Text>
                    </TouchableOpacity>
                  ))}
                </View>

                {/* Bouton générer / régénérer */}
                {!showLetter ? (
                  <TouchableOpacity style={s.generateLetterBtn} activeOpacity={0.85} onPress={handleGenerateLetter} disabled={letterLoading}>
                    {letterLoading
                      ? <ActivityIndicator color="#FFF" />
                      : <Text style={s.generateLetterBtnText}>📄 Générer ma lettre de contestation</Text>
                    }
                  </TouchableOpacity>
                ) : (
                  <>
                    <View style={s.resultCard}>
                      <Text style={s.resultTitle}>📄 Lettre de contestation — {TONES.find(t => t.id === letterTone)?.label}</Text>
                      {letterLoading ? (
                        <ActivityIndicator color="#C45A2D" style={{ marginVertical: 20 }} />
                      ) : (
                        <View style={s.letterBox}>
                          <Text style={s.letterText}>{letterText}</Text>
                        </View>
                      )}
                      <TouchableOpacity style={s.shareBtn} onPress={shareResult}>
                        <Text style={s.shareBtnText}>📤 Partager / Copier la lettre</Text>
                      </TouchableOpacity>
                    </View>

                    <TouchableOpacity
                      style={s.regenBtn}
                      activeOpacity={0.85}
                      onPress={() => handleRegenerateLetter(letterTone)}
                      disabled={letterLoading}
                    >
                      {letterLoading
                        ? <ActivityIndicator color="#FFF" />
                        : <Text style={s.regenBtnText}>🔄 Régénérer avec ce ton</Text>
                      }
                    </TouchableOpacity>
                  </>
                )}
              </>
            )}

            {/* Disclaimer */}
            <View style={s.disclaimer}>
              <Text style={s.disclaimerText}>⚖️ {result.disclaimer || 'Lexavo est un outil d\'information juridique. Il ne remplace pas un avocat.'}</Text>
            </View>

            <TouchableOpacity style={s.resetBtn} onPress={reset}>
              <Text style={s.resetBtnText}>⚡ Nouvelle situation</Text>
            </TouchableOpacity>
          </>
        )}

      </ScrollView>
    </KeyboardAvoidingView>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────
const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F7F8FC' },
  scroll: { paddingBottom: 40 },

  hero: { paddingTop: 52, paddingBottom: 24, paddingHorizontal: 20, alignItems: 'center' },
  heroEmoji: { fontSize: 32, marginBottom: 6 },
  heroTitle: { fontSize: 22, fontWeight: '900', color: '#FFF', letterSpacing: 0.5 },
  heroSub: { fontSize: 12, color: 'rgba(255,255,255,0.65)', marginTop: 4, textAlign: 'center', marginBottom: 16 },

  steps: { flexDirection: 'row', alignItems: 'center' },
  stepDot: { width: 28, height: 28, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.2)', alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: 'rgba(255,255,255,0.4)' },
  stepDotActive: { backgroundColor: '#FFF', borderColor: '#FFF' },
  stepDotDone: { backgroundColor: '#10B981', borderColor: '#10B981' },
  stepNum: { fontSize: 12, fontWeight: '800', color: 'rgba(255,255,255,0.7)' },
  stepLine: { width: 32, height: 2, backgroundColor: 'rgba(255,255,255,0.3)' },
  stepLineDone: { backgroundColor: '#10B981' },

  sectionTitle: { fontSize: 15, fontWeight: '700', color: '#1F2937', marginHorizontal: 16, marginTop: 16, marginBottom: 10 },

  group: { marginHorizontal: 16, marginBottom: 4 },
  groupLabel: { fontSize: 12, fontWeight: '800', color: '#6B7280', letterSpacing: 1, marginBottom: 10, marginTop: 16, textTransform: 'uppercase' },
  catGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  catCard: {
    width: '47%', backgroundColor: '#FFF', borderRadius: 14, padding: 14,
    borderWidth: 1.5, alignItems: 'flex-start',
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, elevation: 2,
  },
  catEmoji: { fontSize: 24, marginBottom: 6 },
  catLabel: { fontSize: 12, fontWeight: '700', color: '#1F2937' },
  checklistBadge: { marginTop: 6, backgroundColor: '#ECFDF5', paddingHorizontal: 7, paddingVertical: 2, borderRadius: 8 },
  checklistBadgeText: { fontSize: 9, fontWeight: '800', color: '#065F46' },

  backBtn: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 4 },
  backText: { color: '#C45A2D', fontSize: 14, fontWeight: '700' },

  catBadge: { marginHorizontal: 16, marginBottom: 12, flexDirection: 'row', alignItems: 'center', padding: 12, borderRadius: 12, borderWidth: 1, gap: 10, flexWrap: 'wrap' },
  catBadgeEmoji: { fontSize: 22 },
  catBadgeLabel: { fontSize: 15, fontWeight: '800' },
  catBadgeSub: { color: '#6B7280', fontSize: 11, width: '100%' },

  scanBox: { marginHorizontal: 16, backgroundColor: '#FFF', borderRadius: 14, padding: 14, marginBottom: 12, borderWidth: 1, borderColor: '#E5E7EB' },
  scanTitle: { fontSize: 14, fontWeight: '700', color: '#1F2937', marginBottom: 4 },
  scanSub: { fontSize: 12, color: '#6B7280', marginBottom: 10 },
  scanBtn: { backgroundColor: '#C45A2D', borderRadius: 10, paddingVertical: 12, alignItems: 'center', marginTop: 8 },
  scanBtnText: { color: '#FFF', fontSize: 14, fontWeight: '700' },

  inputCard: { backgroundColor: '#FFF', borderRadius: 12, padding: 14, marginHorizontal: 16, borderWidth: 1, borderColor: '#E5E7EB', marginBottom: 12 },
  textArea: { minHeight: 100, fontSize: 14, color: '#1F2937', lineHeight: 20 },
  charCount: { textAlign: 'right', fontSize: 11, color: '#9CA3AF', marginTop: 4 },

  regionRow: { flexDirection: 'row', gap: 8, marginHorizontal: 16, marginBottom: 16 },
  regionChip: { flex: 1, paddingVertical: 10, borderRadius: 10, backgroundColor: '#FFF', borderWidth: 1.5, borderColor: '#E5E7EB', alignItems: 'center' },
  regionChipActive: { borderColor: '#C45A2D', backgroundColor: '#FFF7F5' },
  regionText: { fontSize: 12, fontWeight: '600', color: '#6B7280' },
  regionTextActive: { color: '#C45A2D', fontWeight: '800' },

  errorBox: { marginHorizontal: 16, backgroundColor: '#FEF2F2', borderRadius: 10, padding: 12, marginBottom: 12, borderWidth: 1, borderColor: '#FECACA' },
  errorText: { color: '#DC2626', fontSize: 13, fontWeight: '500' },

  // Sélecteur de ton
  toneSub: { fontSize: 11, color: '#6B7280', marginHorizontal: 16, marginTop: -6, marginBottom: 10, fontStyle: 'italic' },
  toneGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginHorizontal: 16, marginBottom: 16 },
  toneChip: {
    backgroundColor: '#FFF', borderRadius: 12, padding: 10, borderWidth: 1.5,
    borderColor: '#E5E7EB', width: '47%',
  },
  toneChipActive: { borderColor: '#C45A2D', backgroundColor: '#FFF7F5' },
  toneLabel: { fontSize: 13, fontWeight: '700', color: '#374151', marginBottom: 2 },
  toneLabelActive: { color: '#C45A2D' },
  toneDesc: { fontSize: 10, color: '#9CA3AF' },
  toneDescActive: { color: '#C45A2D' },

  analyzeBtn: { marginHorizontal: 16, backgroundColor: '#C45A2D', borderRadius: 14, padding: 16, alignItems: 'center', marginBottom: 16 },
  analyzeBtnDisabled: { opacity: 0.6 },
  analyzeBtnText: { color: '#FFF', fontSize: 16, fontWeight: '800' },

  // Bouton régénérer
  regenBtn: {
    marginHorizontal: 16, marginBottom: 16,
    backgroundColor: '#374151', borderRadius: 12, padding: 14, alignItems: 'center',
  },
  regenBtnText: { color: '#FFF', fontSize: 14, fontWeight: '700' },

  // Résultats
  recCard: { marginHorizontal: 16, marginBottom: 12, backgroundColor: '#EFF6FF', borderRadius: 12, padding: 14, borderWidth: 1, borderColor: '#BFDBFE' },
  recText: { fontSize: 14, fontWeight: '700', color: '#1E40AF' },

  resultCard: { backgroundColor: '#FFF', borderRadius: 14, padding: 16, marginHorizontal: 16, marginBottom: 12, borderWidth: 1, borderColor: '#E5E7EB' },
  resultTitle: { fontSize: 14, fontWeight: '800', color: '#1F2937', marginBottom: 10 },
  resultText: { fontSize: 13, color: '#374151', lineHeight: 20 },

  viceRow: { flexDirection: 'row', gap: 8, marginBottom: 6, alignItems: 'flex-start' },
  viceBullet: { fontSize: 14, color: '#10B981', fontWeight: '900', marginTop: 1 },
  viceText: { flex: 1, fontSize: 13, color: '#1F2937', lineHeight: 19 },

  letterBox: { backgroundColor: '#F9FAFB', borderRadius: 10, padding: 14, borderLeftWidth: 3, borderLeftColor: '#C45A2D', marginTop: 8, marginBottom: 10 },
  letterText: { fontSize: 12, color: '#1F2937', lineHeight: 20 },
  shareBtn: { backgroundColor: '#C45A2D', borderRadius: 10, paddingVertical: 12, alignItems: 'center' },
  shareBtnText: { color: '#FFF', fontSize: 13, fontWeight: '700' },

  legalBox: { marginHorizontal: 16, marginBottom: 12, backgroundColor: '#FFFBEB', borderRadius: 12, padding: 14, borderWidth: 1, borderColor: '#FDE68A' },
  legalTitle: { fontSize: 12, fontWeight: '800', color: '#92400E', marginBottom: 6 },
  legalText: { fontSize: 12, color: '#78350F', lineHeight: 18 },

  stepRow: { flexDirection: 'row', gap: 10, marginBottom: 8, alignItems: 'flex-start' },
  stepNum2: { width: 22, height: 22, borderRadius: 11, backgroundColor: '#C45A2D', alignItems: 'center', justifyContent: 'center' },
  stepNumText: { color: '#FFF', fontSize: 11, fontWeight: '700' },
  stepText: { flex: 1, fontSize: 13, color: '#374151', lineHeight: 19 },

  disclaimer: { marginHorizontal: 16, marginBottom: 16, padding: 12, backgroundColor: '#FFFBEB', borderRadius: 10, borderWidth: 1, borderColor: '#FDE68A' },
  disclaimerText: { fontSize: 10, color: '#92400E', textAlign: 'center', lineHeight: 15, fontStyle: 'italic' },

  resetBtn: { marginHorizontal: 16, backgroundColor: '#1F2937', borderRadius: 14, padding: 16, alignItems: 'center' },
  resetBtnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },

  // Séparateur analyse / lettre
  letterSeparator: { flexDirection: 'row', alignItems: 'center', marginHorizontal: 16, marginVertical: 16, gap: 10 },
  letterSepLine: { flex: 1, height: 1, backgroundColor: '#E5E7EB' },
  letterSepText: { fontSize: 11, fontWeight: '700', color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: 1 },

  // Bouton générer lettre
  generateLetterBtn: {
    marginHorizontal: 16, marginBottom: 16,
    backgroundColor: '#1C2B3A',
    borderRadius: 14, padding: 16, alignItems: 'center',
    borderWidth: 2, borderColor: '#C45A2D',
  },
  generateLetterBtnText: { color: '#FFF', fontSize: 15, fontWeight: '800' },
});
