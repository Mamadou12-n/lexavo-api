import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { createProofCase, addProofEntry } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import { LinearGradient } from 'expo-linear-gradient';

const PROOF_GREEN = '#1A6B3A';
const ENTRY_TYPES = [
  { id: 'email',     label: '📧 Email',       color: '#2980B9' },
  { id: 'sms',       label: '💬 SMS',         color: '#27AE60' },
  { id: 'document',  label: '📄 Document',    color: '#8E44AD' },
  { id: 'photo',     label: '📷 Photo',       color: '#E67E22' },
  { id: 'witness',   label: '👤 Témoin',      color: '#C0392B' },
  { id: 'other',     label: '📋 Autre',       color: colors.textMuted },
];

export default function ProofScreen() {
  const [step, setStep]           = useState('create'); // 'create' | 'add'
  const [caseTitle, setCaseTitle] = useState('');
  const [caseDesc, setCaseDesc]   = useState('');
  const [caseId, setCaseId]       = useState(null);

  const [entryType, setEntryType] = useState('document');
  const [entryDesc, setEntryDesc] = useState('');
  const [entryDate, setEntryDate] = useState('');
  const [entries, setEntries]     = useState([]);

  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);
  const [photos, setPhotos] = useState([]);

  const createCase = async () => {
    if (!caseTitle.trim()) return;
    setLoading(true); setError(null);
    try {
      const data = await createProofCase(caseTitle.trim(), caseDesc.trim());
      setCaseId(data.case_id);
      setStep('add');
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally {
      setLoading(false);
    }
  };

  const addEntry = async () => {
    if (!entryDesc.trim() || !caseId) return;
    setLoading(true); setError(null);
    try {
      const today = entryDate.trim() || new Date().toISOString().slice(0, 10);
      const data = await addProofEntry(caseId, entryType, entryDesc.trim(), today);
      setEntries((e) => [...e, { type: entryType, description: entryDesc.trim(), date: today, ...data }]);
      setEntryDesc('');
      setEntryDate('');
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur');
    } finally {
      setLoading(false);
    }
  };

  const entryTypeObj = ENTRY_TYPES.find((t) => t.id === entryType);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        <LinearGradient colors={['#0A3D1A', '#1A6B3A']} style={styles.heroHeader}>
          <Text style={styles.heroEmoji}>🗂️</Text>
          <Text style={styles.heroTitle}>Proof — Dossier de preuves</Text>
          <Text style={styles.heroSub}>Constituez votre dossier juridique</Text>
        </LinearGradient>

        {step === 'create' ? (
          <View style={styles.card}>
            <Text style={styles.fieldLabel}>Titre du dossier</Text>
            <TextInput
              style={styles.input}
              placeholder="Ex: Litige bailleur — garantie locative"
              placeholderTextColor={colors.textMuted}
              value={caseTitle}
              onChangeText={setCaseTitle}
              accessibilityLabel="Titre du dossier"
            />

            <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Description (optionnel)</Text>
            <TextInput
              style={[styles.textArea, { minHeight: 80 }]}
              multiline
              placeholder="Contexte du litige, parties impliquées..."
              placeholderTextColor={colors.textMuted}
              value={caseDesc}
              onChangeText={setCaseDesc}
              textAlignVertical="top"
              accessibilityLabel="Description du dossier"
            />

            <PhotoPicker photos={photos} onPhotosChange={setPhotos} label="📷 Ajouter une preuve photo" />

            <TouchableOpacity activeOpacity={0.75}
              style={[styles.btn, (!caseTitle.trim() || loading) && styles.btnDisabled]}
              onPress={createCase}
              disabled={!caseTitle.trim() || loading}
            >
              {loading
                ? <ActivityIndicator color="#FFF" />
                : <Text style={styles.btnText}>🗂️  Créer le dossier</Text>
              }
            </TouchableOpacity>
          </View>
        ) : (
          <>
            {/* Case header */}
            <View style={styles.caseHeader}>
              <Text style={styles.caseTitle}>{caseTitle}</Text>
              <Text style={styles.caseId}>#{caseId}</Text>
              <Text style={styles.caseEntriesCount}>{entries.length} pièce{entries.length > 1 ? 's' : ''}</Text>
            </View>

            {/* Add entry form */}
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Ajouter une pièce</Text>
              <Text style={styles.fieldLabel}>Type de preuve</Text>
              <View style={styles.typeRow}>
                {ENTRY_TYPES.map((t) => (
                  <TouchableOpacity activeOpacity={0.75}
                    key={t.id}
                    style={[styles.typeChip, entryType === t.id && { borderColor: t.color, backgroundColor: `${t.color}15` }]}
                    onPress={() => setEntryType(t.id)}
                  >
                    <Text style={[styles.typeLabel, entryType === t.id && { color: t.color, fontWeight: '700' }]}>
                      {t.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={[styles.fieldLabel, { marginTop: 10 }]}>Description</Text>
              <TextInput
                style={styles.textArea}
                multiline
                numberOfLines={3}
                placeholder="Décrivez cette pièce : contenu, origine, pertinence..."
                placeholderTextColor={colors.textMuted}
                value={entryDesc}
                onChangeText={setEntryDesc}
                textAlignVertical="top"
                accessibilityLabel="Description de la pièce"
              />

              <Text style={[styles.fieldLabel, { marginTop: 10 }]}>Date de la preuve</Text>
              <TextInput
                style={styles.input}
                placeholder="AAAA-MM-JJ"
                placeholderTextColor={colors.textMuted}
                value={entryDate}
                onChangeText={setEntryDate}
                accessibilityLabel="Date de la preuve"
              />

              <TouchableOpacity activeOpacity={0.75}
                style={[styles.btn, (!entryDesc.trim() || loading) && styles.btnDisabled]}
                onPress={addEntry}
                disabled={!entryDesc.trim() || loading}
              >
                {loading
                  ? <ActivityIndicator color="#FFF" />
                  : <Text style={styles.btnText}>+ Ajouter la pièce</Text>
                }
              </TouchableOpacity>
            </View>

            {/* Entries list */}
            {entries.length > 0 && (
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Pièces au dossier ({entries.length})</Text>
                {entries.map((e, i) => {
                  const t = ENTRY_TYPES.find((x) => x.id === e.type);
                  return (
                    <View key={i} style={[styles.entryItem, { borderLeftColor: t?.color ?? colors.primary }]}>
                      <View style={styles.entryHeader}>
                        <Text style={styles.entryType}>{t?.label ?? e.type}</Text>
                        <Text style={styles.entryDate}>{e.date}</Text>
                      </View>
                      <Text style={styles.entryDesc}>{e.description}</Text>
                    </View>
                  );
                })}
              </View>
            )}
          </>
        )}

        <View style={{ margin: 16, padding: 10, backgroundColor: '#FFFBEB', borderRadius: 8, borderWidth: 1, borderColor: '#FDE68A' }}>
          <Text style={{ fontSize: 10, color: '#92400E', textAlign: 'center', fontStyle: 'italic', lineHeight: 14 }}>
            ⚖️ Lexavo est un outil d'information juridique. Il ne remplace pas un avocat ni un conseiller juridique professionnel.
          </Text>
        </View>

        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>⚠️ {error}</Text>
          </View>
        )}
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

  sectionTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 },
  fieldLabel:   { fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 6 },

  input: {
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: 10,
    fontSize: 14,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.border,
  },
  textArea: {
    backgroundColor: colors.background,
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    color: colors.textPrimary,
    minHeight: 90,
    borderWidth: 1,
    borderColor: colors.border,
    lineHeight: 20,
  },

  btn: {
    backgroundColor: PROOF_GREEN,
    borderRadius: 12,
    paddingVertical: 13,
    alignItems: 'center',
    marginTop: 12,
  },
  btnDisabled: { opacity: 0.45 },
  btnText: { color: '#FFF', fontSize: 14, fontWeight: '700' },

  caseHeader: {
    backgroundColor: PROOF_GREEN,
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
  },
  caseTitle:       { color: '#FFF', fontSize: 15, fontWeight: '700' },
  caseId:          { color: 'rgba(255,255,255,0.6)', fontSize: 11, fontFamily: 'monospace', marginTop: 2 },
  caseEntriesCount: { color: '#BBF7D0', fontSize: 12, fontWeight: '600', marginTop: 4 },

  typeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  typeChip: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 10,
    paddingVertical: 5,
    backgroundColor: colors.background,
  },
  typeLabel: { fontSize: 11, color: colors.textSecondary },

  entryItem: {
    borderLeftWidth: 3,
    borderRadius: 6,
    padding: 10,
    marginBottom: 8,
    backgroundColor: '#FAFAFA',
  },
  entryHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  entryType:   { fontSize: 11, fontWeight: '700', color: colors.textSecondary },
  entryDate:   { fontSize: 10, color: colors.textMuted },
  entryDesc:   { fontSize: 12, color: colors.textPrimary, lineHeight: 17 },

  errorBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#FCA5A5',
    marginBottom: 16,
  },
  errorText: { fontSize: 13, color: colors.error, fontWeight: '600' },
});
