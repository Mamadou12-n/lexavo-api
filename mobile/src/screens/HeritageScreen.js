import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { getHeritageGuide } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import ModelBadge from '../components/ModelBadge';
import { LinearGradient } from 'expo-linear-gradient';

const HERITAGE_BROWN = '#8B4513';

const REGIONS = [
  { id: 'bruxelles', label: '🏙️ Bruxelles', sub: 'Région de Bruxelles-Capitale' },
  { id: 'wallonie',  label: '🌿 Wallonie',   sub: 'Droits perçus au profit de la Région wallonne' },
  { id: 'flandre',   label: '🦁 Flandre',    sub: 'Erfbelasting — Vlaamse Belastingdienst' },
];

const HEIR_TYPES = ['enfant', 'conjoint', 'parent', 'frere_soeur', 'autre'];

export default function HeritageScreen() {
  const [region, setRegion]         = useState('bruxelles');
  const [estateValue, setEstate]    = useState('');
  const [heirType, setHeirType]     = useState('enfant');
  const [numHeirs, setNumHeirs]     = useState('1');
  const [loading, setLoading]       = useState(false);
  const [result, setResult]         = useState(null);
  const [error, setError]           = useState(null);
  const [photos, setPhotos] = useState([]);

  const generate = async () => {
    if (!estateValue) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const heirs = Array.from({ length: parseInt(numHeirs) || 1 }, (_, i) => ({
        id: i + 1,
        type: heirType,
        name: `Héritier ${i + 1}`,
      }));
      const data = await getHeritageGuide(region, parseFloat(estateValue), heirs);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        <LinearGradient colors={['#3D1F00', '#8B4513']} style={styles.heroHeader}>
          <Text style={styles.heroEmoji}>🏛️</Text>
          <Text style={styles.heroTitle}>Héritage — Guide successoral</Text>
          <Text style={styles.heroSub}>Droits de succession belges par région</Text>
        </LinearGradient>

        <View style={styles.card}>
          <Text style={styles.fieldLabel}>Région</Text>
          {REGIONS.map((r) => (
            <TouchableOpacity activeOpacity={0.75}
              key={r.id}
              style={[styles.regionBtn, region === r.id && styles.regionBtnActive]}
              onPress={() => setRegion(r.id)}
            >
              <Text style={styles.regionEmoji}>{r.label.split(' ')[0]}</Text>
              <View style={styles.regionInfo}>
                <Text style={[styles.regionName, region === r.id && styles.regionNameActive]}>
                  {r.label.split(' ').slice(1).join(' ')}
                </Text>
                <Text style={styles.regionSub}>{r.sub}</Text>
              </View>
              {region === r.id && <Text style={styles.regionCheck}>✓</Text>}
            </TouchableOpacity>
          ))}

          <Text style={[styles.fieldLabel, { marginTop: 14 }]}>Valeur de la succession (€)</Text>
          <TextInput
            style={styles.input}
            placeholder="Ex: 250000"
            placeholderTextColor={colors.textMuted}
            value={estateValue}
            onChangeText={setEstate}
            keyboardType="numeric"
            accessibilityLabel="Valeur de la succession"
          />

          <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Type d'héritier principal</Text>
          <View style={styles.heirRow}>
            {HEIR_TYPES.map((h) => (
              <TouchableOpacity activeOpacity={0.75}
                key={h}
                style={[styles.heirChip, heirType === h && styles.heirChipActive]}
                onPress={() => setHeirType(h)}
              >
                <Text style={[styles.heirLabel, heirType === h && styles.heirLabelActive]}>
                  {h.replace('_', ' ')}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Nombre d'héritiers</Text>
          <TextInput
            style={styles.input}
            placeholder="Ex: 2"
            placeholderTextColor={colors.textMuted}
            value={numHeirs}
            onChangeText={setNumHeirs}
            keyboardType="numeric"
            accessibilityLabel="Nombre d'héritiers"
          />

          <PhotoPicker photos={photos} onPhotosChange={setPhotos} />

            <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, (!estateValue || loading) && styles.btnDisabled]}
            onPress={generate}
            disabled={!estateValue || loading}
          >
            {loading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>🏛️  Générer le guide successoral</Text>
            }
          </TouchableOpacity>
        </View>

        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>⚠️ {error}</Text>
          </View>
        )}

        {result && (
          <View style={styles.card}>
            <ModelBadge model={result.model} />
            {/* Summary */}
            {result.summary && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Vue d'ensemble</Text>
                <Text style={styles.bodyText}>{result.summary}</Text>
              </View>
            )}

            {/* Succession duties */}
            {result.succession_duties != null && (
              <View style={styles.dutyBox}>
                <Text style={styles.dutyLabel}>Droits de succession estimés</Text>
                <Text style={styles.dutyValue}>
                  {result.succession_duties.toLocaleString('fr-BE', { maximumFractionDigits: 0 })} €
                </Text>
                {result.effective_rate != null && (
                  <Text style={styles.dutyRate}>Taux effectif : {result.effective_rate.toFixed(1)}%</Text>
                )}
              </View>
            )}

            {/* Steps */}
            {result.steps?.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Étapes de la succession</Text>
                {result.steps.map((s, i) => (
                  <View key={i} style={styles.stepItem}>
                    <View style={styles.stepCircle}>
                      <Text style={styles.stepNum}>{i + 1}</Text>
                    </View>
                    <View style={styles.stepContent}>
                      <Text style={styles.stepTitle}>{typeof s === 'string' ? s : s.title}</Text>
                      {s.deadline && <Text style={styles.stepDeadline}>⏱ {s.deadline}</Text>}
                    </View>
                  </View>
                ))}
              </View>
            )}

            {/* Fiscal rates */}
            {result.applicable_rates && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Barème applicable ({region})</Text>
                {Object.entries(result.applicable_rates).map(([bracket, rate]) => (
                  <View key={bracket} style={styles.rateRow}>
                    <Text style={styles.rateBracket}>{bracket}</Text>
                    <Text style={styles.rateValue}>{rate}</Text>
                  </View>
                ))}
              </View>
            )}

            {result.legal_basis && (
              <View style={styles.legalBox}>
                <Text style={styles.legalText}>📖 {result.legal_basis}</Text>
              </View>
            )}

            {result.disclaimer && (
              <Text style={styles.disclaimer}>{result.disclaimer}</Text>
            )}
          </View>
        )}
        <View style={{ marginTop: 12, padding: 10, backgroundColor: '#FFFBEB', borderRadius: 8, borderWidth: 1, borderColor: '#FDE68A' }}>
          <Text style={{ fontSize: 10, color: '#92400E', textAlign: 'center', fontStyle: 'italic', lineHeight: 14 }}>
            {'\u2696\ufe0f Lexavo est un outil d\'information juridique. Il ne remplace pas un avocat ni un conseiller juridique professionnel.'}
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content:   { padding: 16, paddingBottom: 40 },

  heroHeader: { borderRadius: 16, padding: 20, marginBottom: 16, alignItems: 'center' },
  heroEmoji: { fontSize: 32, marginBottom: 8 },
  heroTitle: { fontSize: 20, fontWeight: '900', color: '#FFF', letterSpacing: 0.5 },
  heroSub: { fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4, textAlign: 'center' },

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

  fieldLabel: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },

  regionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 11,
    marginBottom: 7,
    backgroundColor: colors.background,
  },
  regionBtnActive: { borderColor: HERITAGE_BROWN, backgroundColor: '#FDF5ED' },
  regionEmoji:     { fontSize: 18 },
  regionInfo:      { flex: 1 },
  regionName:      { fontSize: 13, fontWeight: '600', color: colors.textPrimary },
  regionNameActive: { color: HERITAGE_BROWN },
  regionSub:       { fontSize: 10, color: colors.textMuted, marginTop: 1 },
  regionCheck:     { fontSize: 15, color: HERITAGE_BROWN, fontWeight: '700' },

  input: {
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: 10,
    fontSize: 14,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 4,
  },

  heirRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 7 },
  heirChip: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 10,
    paddingVertical: 5,
    backgroundColor: colors.background,
  },
  heirChipActive:  { borderColor: HERITAGE_BROWN, backgroundColor: '#FDF5ED' },
  heirLabel:       { fontSize: 11, color: colors.textSecondary },
  heirLabelActive: { color: HERITAGE_BROWN, fontWeight: '700' },

  btn: {
    backgroundColor: HERITAGE_BROWN,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 14,
  },
  btnDisabled: { opacity: 0.45 },
  btnText: { color: '#FFF', fontSize: 14, fontWeight: '700' },

  errorBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#FCA5A5',
    marginBottom: 16,
  },
  errorText: { fontSize: 13, color: colors.error, fontWeight: '600' },

  section:      { marginBottom: 14 },
  sectionTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  bodyText:     { fontSize: 14, color: colors.textPrimary, lineHeight: 21 },

  dutyBox: {
    backgroundColor: '#FDF5ED',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#F5D5B0',
  },
  dutyLabel: { fontSize: 11, color: '#92400E', marginBottom: 4 },
  dutyValue: { fontSize: 30, fontWeight: '900', color: HERITAGE_BROWN },
  dutyRate:  { fontSize: 11, color: '#92400E', marginTop: 4 },

  stepItem: { flexDirection: 'row', gap: 10, marginBottom: 8, alignItems: 'flex-start' },
  stepCircle: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: HERITAGE_BROWN,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  stepNum:     { color: '#FFF', fontSize: 11, fontWeight: '700' },
  stepContent: { flex: 1 },
  stepTitle:   { fontSize: 13, color: colors.textPrimary, lineHeight: 19 },
  stepDeadline: { fontSize: 11, color: colors.textMuted, marginTop: 2 },

  rateRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  rateBracket: { fontSize: 12, color: colors.textSecondary },
  rateValue:   { fontSize: 12, fontWeight: '700', color: HERITAGE_BROWN },

  legalBox: { backgroundColor: colors.surfaceAlt, borderRadius: 8, padding: 10, marginBottom: 10 },
  legalText: { fontSize: 11, color: colors.textSecondary },
  disclaimer: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic', textAlign: 'center' },
});
