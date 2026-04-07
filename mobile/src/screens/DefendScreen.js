/**
 * DefendScreen — Lexavo Defend
 * Contestation, recours et generation de documents juridiques.
 * 8 categories, detection auto, document genere, prochaines etapes.
 */

import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { defendAnalyze, REGION_KEY } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import { LinearGradient } from 'expo-linear-gradient';

const CATEGORIES = [
  { id: null,           label: 'Auto-detect', emoji: '🔍' },
  { id: 'amende',       label: 'Amende',      emoji: '🚗' },
  { id: 'consommation', label: 'Conso',       emoji: '🛒' },
  { id: 'bail',         label: 'Bail',         emoji: '🏠' },
  { id: 'travail',      label: 'Travail',      emoji: '👷' },
  { id: 'huissier',     label: 'Huissier',     emoji: '📨' },
  { id: 'social',       label: 'Social',       emoji: '🏥' },
  { id: 'scolaire',     label: 'Scolaire',     emoji: '🎓' },
  { id: 'fiscal',       label: 'Fiscal',       emoji: '💰' },
];

const REGIONS = [
  { id: 'bruxelles', label: '🏙️ Bruxelles' },
  { id: 'wallonie',  label: '🟡 Wallonie' },
  { id: 'flandre',   label: '🦁 Flandre' },
];

const PROBABILITY_CONFIG = {
  elevee:       { color: '#10B981', bg: '#ECFDF5', label: 'Elevee',       icon: '🟢' },
  moyenne:      { color: '#F59E0B', bg: '#FFFBEB', label: 'Moyenne',      icon: '🟠' },
  faible:       { color: '#EF4444', bg: '#FEF2F2', label: 'Faible',       icon: '🔴' },
  indeterminee: { color: '#6B7280', bg: '#F3F4F6', label: 'Indeterminee', icon: '⚪' },
};

export default function DefendScreen() {
  const [description, setDescription]     = useState('');
  const [category, setCategory]           = useState(null);
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [loading, setLoading]             = useState(false);
  const [result, setResult]               = useState(null);
  const [error, setError]                 = useState(null);
  const [photos, setPhotos]               = useState([]);

  const analyze = async () => {
    if (description.trim().length < 20) {
      setError('Decrivez votre situation en au moins 20 caracteres.');
      return;
    }
    setLoading(true); setResult(null); setError(null);
    try {
      const region = selectedRegion || await AsyncStorage.getItem(REGION_KEY);

      const data = await defendAnalyze(
        description.trim(),
        category,
        region || null,
        '',
        photos,
      );
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur reseau');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setResult(null);
    setDescription('');
    setCategory(null);
    setError(null);
    setPhotos([]);
  };

  const prob = result ? PROBABILITY_CONFIG[result.success_probability] || PROBABILITY_CONFIG.indeterminee : null;

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        {/* Header */}
        <LinearGradient colors={['#7C2D12', '#C45A2D']} style={styles.heroHeader}>
          <Text style={styles.heroEmoji}>⚡</Text>
          <Text style={styles.heroTitle}>Lexavo Defend</Text>
          <Text style={styles.heroSub}>Contestez, reclamez, agissez — en 30 secondes</Text>
        </LinearGradient>

        {!result ? (
          <>
            {/* Categories */}
            <Text style={styles.sectionTitle}>Categorie</Text>
            <View style={styles.typesRow}>
              {CATEGORIES.map(c => (
                <TouchableOpacity activeOpacity={0.75}
                  key={c.id || 'auto'}
                  style={[styles.typeChip, category === c.id && styles.typeChipActive]}
                  onPress={() => setCategory(c.id)}
                >
                  <Text style={[styles.typeChipText, category === c.id && styles.typeChipTextActive]}>
                    {c.emoji} {c.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Region */}
            <Text style={styles.sectionTitle}>Region</Text>
            <View style={styles.typesRow}>
              {REGIONS.map(r => (
                <TouchableOpacity activeOpacity={0.75}
                  key={r.id}
                  style={[styles.typeChip, selectedRegion === r.id && styles.typeChipActive]}
                  onPress={() => setSelectedRegion(selectedRegion === r.id ? null : r.id)}
                >
                  <Text style={[styles.typeChipText, selectedRegion === r.id && styles.typeChipTextActive]}>
                    {r.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Description */}
            <View style={styles.inputCard}>
              <TextInput
                style={styles.textArea}
                multiline
                numberOfLines={6}
                placeholder="Decrivez votre situation en detail (minimum 20 caracteres)..."
                placeholderTextColor={colors.textMuted}
                value={description}
                onChangeText={setDescription}
                textAlignVertical="top"
                accessibilityLabel="Description de la situation"
              />
              <Text style={styles.charCount}>
                {description.length} caractere{description.length !== 1 ? 's' : ''}
              </Text>
            </View>

            {/* Error */}
            {error && (
              <View style={styles.errorBox}>
                <Text style={styles.errorText}>⚠️ {error}</Text>
              </View>
            )}

            {/* Photo */}
            <PhotoPicker photos={photos} onPhotosChange={setPhotos} />

            {/* Submit */}
            <TouchableOpacity activeOpacity={0.75}
              style={[styles.analyzeBtn, loading && styles.analyzeBtnDisabled]}
              onPress={analyze}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#FFF" />
              ) : (
                <Text style={styles.analyzeBtnText}>⚡ Analyser ma situation</Text>
              )}
            </TouchableOpacity>
          </>
        ) : (
          <>
            {/* ═══ RESULTAT ═══ */}

            {/* Detection */}
            {result.detection && (
              <View style={styles.resultCard}>
                <Text style={styles.resultCardTitle}>🔍 Detection automatique</Text>
                <View style={styles.detectionRow}>
                  <Text style={styles.detectionLabel}>Categorie :</Text>
                  <View style={styles.detectionBadge}>
                    <Text style={styles.detectionBadgeText}>{result.detection.category || 'N/A'}</Text>
                  </View>
                </View>
                {result.detection.urgency && (
                  <View style={styles.detectionRow}>
                    <Text style={styles.detectionLabel}>Urgence :</Text>
                    <Text style={styles.detectionValue}>{result.detection.urgency}</Text>
                  </View>
                )}
              </View>
            )}

            {/* Analyse */}
            {result.situation_analysis && (
              <View style={styles.resultCard}>
                <Text style={styles.resultCardTitle}>📋 Analyse de la situation</Text>
                <Text style={styles.resultText}>{result.situation_analysis}</Text>
              </View>
            )}

            {/* Probabilite */}
            {prob && (
              <View style={[styles.probabilityCard, { backgroundColor: prob.bg }]}>
                <Text style={styles.probabilityIcon}>{prob.icon}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={styles.probabilityLabel}>Probabilite de succes</Text>
                  <Text style={[styles.probabilityValue, { color: prob.color }]}>{prob.label}</Text>
                </View>
                {result.contestation_possible && (
                  <View style={styles.contestBadge}>
                    <Text style={styles.contestBadgeText}>Contestable</Text>
                  </View>
                )}
              </View>
            )}

            {/* Lois applicables */}
            {result.applicable_law?.length > 0 && (
              <View style={styles.resultCard}>
                <Text style={styles.resultCardTitle}>⚖️ Base legale</Text>
                {result.applicable_law.map((law, i) => (
                  <View key={i} style={styles.lawItem}>
                    <Text style={styles.lawArticle}>{law.article}</Text>
                    <Text style={styles.lawContent}>{law.content}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Document genere */}
            {result.document_text && (
              <View style={styles.resultCard}>
                <Text style={styles.resultCardTitle}>
                  📄 {result.document_type === 'contestation' ? 'Lettre de contestation' : 'Document genere'}
                </Text>
                {result.recipient && (
                  <Text style={styles.recipientText}>Destinataire : {result.recipient}</Text>
                )}
                <View style={styles.documentBox}>
                  <Text style={styles.documentText}>{result.document_text}</Text>
                </View>
                {result.deadline && (
                  <Text style={styles.deadlineText}>⏰ Delai : {result.deadline}</Text>
                )}
              </View>
            )}

            {/* Prochaines etapes */}
            {result.next_steps?.length > 0 && (
              <View style={styles.resultCard}>
                <Text style={styles.resultCardTitle}>📌 Prochaines etapes</Text>
                {result.next_steps.map((step, i) => (
                  <View key={i} style={styles.stepItem}>
                    <Text style={styles.stepNumber}>{i + 1}</Text>
                    <Text style={styles.stepText}>{step}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Disclaimer */}
            <View style={styles.disclaimer}>
              <Text style={styles.disclaimerText}>
                ⚖️ Ce document est un modele indicatif. Il ne constitue pas un acte d'avocat.
                En cas de litige complexe, consultez un professionnel du droit.
              </Text>
            </View>

            {/* Nouvelle analyse */}
            <TouchableOpacity activeOpacity={0.75} style={styles.resetBtn} onPress={resetForm}>
              <Text style={styles.resetBtnText}>⚡ Nouvelle situation</Text>
            </TouchableOpacity>
          </>
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

  heroHeader: { borderRadius: 16, padding: 20, marginBottom: 16, alignItems: 'center' },
  heroEmoji: { fontSize: 32, marginBottom: 8 },
  heroTitle: { fontSize: 20, fontWeight: '900', color: '#FFF', letterSpacing: 0.5 },
  heroSub: { fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4, textAlign: 'center' },

  sectionTitle: {
    fontSize: 14, fontWeight: '700', color: colors.textPrimary,
    marginBottom: 8, marginTop: 4,
  },

  typesRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 },
  typeChip: {
    paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20,
    backgroundColor: colors.surface, borderWidth: 1.5, borderColor: colors.border,
  },
  typeChipActive: { backgroundColor: '#C45A2D', borderColor: '#C45A2D' },
  typeChipText: { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  typeChipTextActive: { color: '#FFF' },

  inputCard: {
    backgroundColor: colors.surface, borderRadius: 12, padding: 14,
    borderWidth: 1, borderColor: colors.border, marginBottom: 12,
  },
  textArea: {
    minHeight: 120, fontSize: 14, color: colors.textPrimary, lineHeight: 20,
  },
  charCount: {
    textAlign: 'right', fontSize: 11, color: colors.textMuted, marginTop: 6,
  },

  errorBox: {
    backgroundColor: '#FEF2F2', borderRadius: 10, padding: 12, marginBottom: 12,
    borderWidth: 1, borderColor: '#FECACA',
  },
  errorText: { color: '#DC2626', fontSize: 13, fontWeight: '500' },

  analyzeBtn: {
    backgroundColor: '#C45A2D', borderRadius: 14, padding: 16,
    alignItems: 'center', marginBottom: 16,
  },
  analyzeBtnDisabled: { opacity: 0.6 },
  analyzeBtnText: { color: '#FFF', fontSize: 16, fontWeight: '800' },

  // Result
  resultCard: {
    backgroundColor: colors.surface, borderRadius: 12, padding: 16,
    borderWidth: 1, borderColor: colors.border, marginBottom: 12,
  },
  resultCardTitle: { fontSize: 15, fontWeight: '700', color: colors.textPrimary, marginBottom: 10 },
  resultText: { fontSize: 13, color: colors.textSecondary, lineHeight: 20 },

  detectionRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  detectionLabel: { fontSize: 13, color: colors.textSecondary, width: 90 },
  detectionValue: { fontSize: 13, color: colors.textPrimary, fontWeight: '600' },
  detectionBadge: {
    backgroundColor: 'rgba(196,90,45,0.12)', paddingHorizontal: 10, paddingVertical: 3,
    borderRadius: 10,
  },
  detectionBadgeText: { fontSize: 12, fontWeight: '700', color: '#C45A2D', textTransform: 'capitalize' },

  probabilityCard: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    borderRadius: 12, padding: 16, marginBottom: 12,
  },
  probabilityIcon: { fontSize: 28 },
  probabilityLabel: { fontSize: 12, color: colors.textSecondary },
  probabilityValue: { fontSize: 18, fontWeight: '800' },
  contestBadge: {
    backgroundColor: '#10B981', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8,
  },
  contestBadgeText: { color: '#FFF', fontSize: 11, fontWeight: '700' },

  lawItem: {
    backgroundColor: colors.surfaceAlt, borderRadius: 8, padding: 10, marginBottom: 6,
  },
  lawArticle: { fontSize: 12, fontWeight: '700', color: colors.primary, marginBottom: 2 },
  lawContent: { fontSize: 12, color: colors.textSecondary, lineHeight: 18 },

  documentBox: {
    backgroundColor: colors.surfaceAlt, borderRadius: 8, padding: 12, marginTop: 8,
    borderLeftWidth: 3, borderLeftColor: '#C45A2D',
  },
  documentText: { fontSize: 12, color: colors.textPrimary, lineHeight: 19 },
  recipientText: { fontSize: 12, color: colors.textSecondary, marginBottom: 6, fontStyle: 'italic' },
  deadlineText: { fontSize: 12, color: '#EF4444', fontWeight: '600', marginTop: 8 },

  stepItem: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 8 },
  stepNumber: {
    width: 22, height: 22, borderRadius: 11, backgroundColor: '#C45A2D',
    color: '#FFF', fontSize: 12, fontWeight: '700', textAlign: 'center', lineHeight: 22,
  },
  stepText: { flex: 1, fontSize: 13, color: colors.textSecondary, lineHeight: 18 },

  disclaimer: {
    backgroundColor: '#FFFBEB', borderRadius: 10, padding: 12, marginBottom: 16,
    borderWidth: 1, borderColor: '#FDE68A',
  },
  disclaimerText: { fontSize: 11, color: '#92400E', lineHeight: 16 },

  resetBtn: {
    backgroundColor: colors.primary, borderRadius: 14, padding: 16,
    alignItems: 'center', marginBottom: 16,
  },
  resetBtnText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
});
