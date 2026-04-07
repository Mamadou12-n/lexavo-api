import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { startLitigation } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import { LinearGradient } from 'expo-linear-gradient';

const LITIGE_RED = '#B22222';
const STAGE_COLOR = ['#E74C3C', '#E67E22', '#C0392B', '#8B0000'];

export default function LitigesScreen() {
  const [creditorName, setCreditor]   = useState('');
  const [debtorName, setDebtor]       = useState('');
  const [amount, setAmount]           = useState('');
  const [invoiceNumber, setInvoice]   = useState('');
  const [dueDate, setDueDate]         = useState('');
  const [loading, setLoading]         = useState(false);
  const [result, setResult]           = useState(null);
  const [error, setError]             = useState(null);
  const [photos, setPhotos] = useState([]);

  const start = async () => {
    if (!creditorName || !debtorName || !amount) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const data = await startLitigation({
        creditor_name: creditorName.trim(),
        debtor_name: debtorName.trim(),
        amount: parseFloat(amount),
        invoice_number: invoiceNumber.trim() || 'FAC-XXXX',
        due_date: dueDate.trim() || new Date().toISOString().slice(0, 10),
      }, photos);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally {
      setLoading(false);
    }
  };

  const STAGE_ICONS = ['📧', '📮', '📬', '⚖️'];

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        <LinearGradient colors={['#5B1A1A', '#B22222']} style={styles.heroHeader}>
          <Text style={styles.heroEmoji}>⚖️</Text>
          <Text style={styles.heroTitle}>Litiges — Recouvrement</Text>
          <Text style={styles.heroSub}>Procédure amiable → IOS en 4 étapes</Text>
        </LinearGradient>

        <View style={styles.card}>
          {[
            { label: 'Votre nom / entreprise (créancier)', val: creditorName, set: setCreditor, placeholder: 'Ex: Mon Entreprise SPRL' },
            { label: 'Débiteur', val: debtorName, set: setDebtor, placeholder: 'Ex: Client Défaillant SA' },
            { label: 'Montant impayé (€)', val: amount, set: setAmount, placeholder: 'Ex: 3500', kb: 'numeric' },
            { label: 'N° de facture', val: invoiceNumber, set: setInvoice, placeholder: 'Ex: FAC-2025-042' },
            { label: 'Date d\'échéance', val: dueDate, set: setDueDate, placeholder: 'AAAA-MM-JJ' },
          ].map((f, i) => (
            <View key={i} style={styles.fieldWrap}>
              <Text style={styles.fieldLabel}>{f.label}</Text>
              <TextInput
                style={styles.input}
                placeholder={f.placeholder}
                placeholderTextColor={colors.textMuted}
                value={f.val}
                onChangeText={f.set}
                keyboardType={f.kb ?? 'default'}
                accessibilityLabel={f.label}
              />
            </View>
          ))}

          <PhotoPicker photos={photos} onPhotosChange={setPhotos} />

            <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, (!creditorName || !debtorName || !amount || loading) && styles.btnDisabled]}
            onPress={start}
            disabled={!creditorName || !debtorName || !amount || loading}
          >
            {loading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>⚖️  Démarrer la procédure</Text>
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
            <View style={styles.litigationIdRow}>
              <Text style={styles.litigationIdLabel}>Dossier</Text>
              <Text style={styles.litigationId}>{result.litigation_id}</Text>
            </View>

            {/* Current stage */}
            {result.current_stage && (
              <View style={styles.currentStage}>
                <Text style={styles.currentStageLabel}>Étape en cours</Text>
                <Text style={styles.currentStageName}>
                  {STAGE_ICONS[0]} {result.current_stage.replace(/_/g, ' ').toUpperCase()}
                </Text>
              </View>
            )}

            {/* Timeline */}
            {result.stages?.length > 0 && (
              <View style={styles.timeline}>
                {result.stages.map((stage, i) => (
                  <View key={i} style={styles.timelineItem}>
                    <View style={[styles.timelineDot, {
                      backgroundColor: stage.status === 'active' ? STAGE_COLOR[i] : colors.border,
                    }]}>
                      <Text style={styles.timelineDotText}>{i + 1}</Text>
                    </View>
                    <View style={styles.timelineContent}>
                      <Text style={[styles.timelineName, stage.status === 'active' && { color: STAGE_COLOR[i] }]}>
                        {STAGE_ICONS[i]} {stage.name?.replace(/_/g, ' ')}
                      </Text>
                      <Text style={styles.timelineDate}>J+{[15, 30, 45, 60][i]} · {stage.scheduled_date}</Text>
                      <View style={[styles.statusPill, {
                        backgroundColor: stage.status === 'active' ? '#FEF2F2' : '#F3F4F6',
                      }]}>
                        <Text style={[styles.statusPillText, {
                          color: stage.status === 'active' ? LITIGE_RED : colors.textMuted,
                        }]}>
                          {stage.status}
                        </Text>
                      </View>
                    </View>
                  </View>
                ))}
              </View>
            )}

            {/* First letter preview */}
            {result.current_letter && (
              <View style={styles.letterPreview}>
                <Text style={styles.letterPreviewTitle}>📬 Lettre générée</Text>
                <Text style={styles.letterPreviewText} numberOfLines={8}>{result.current_letter}</Text>
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
            ⚖️ Lexavo est un outil d'information juridique. Il ne remplace pas un avocat ni un conseiller juridique professionnel.
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

  fieldWrap: { marginBottom: 10 },
  fieldLabel: { fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 4 },
  input: {
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: 10,
    fontSize: 14,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.border,
  },

  btn: {
    backgroundColor: LITIGE_RED,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 6,
  },
  btnDisabled: { opacity: 0.45 },
  btnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },

  errorBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#FCA5A5',
    marginBottom: 16,
  },
  errorText: { fontSize: 13, color: colors.error, fontWeight: '600' },

  litigationIdRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  litigationIdLabel: { fontSize: 11, color: colors.textMuted },
  litigationId: { fontSize: 13, fontWeight: '700', color: LITIGE_RED, fontFamily: 'monospace' },

  currentStage: {
    backgroundColor: '#FEF2F2',
    borderRadius: 8,
    padding: 10,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#FCA5A5',
  },
  currentStageLabel: { fontSize: 10, color: colors.textMuted, marginBottom: 2 },
  currentStageName:  { fontSize: 14, fontWeight: '700', color: LITIGE_RED },

  timeline: { marginBottom: 14 },
  timelineItem: { flexDirection: 'row', gap: 10, marginBottom: 10 },
  timelineDot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  timelineDotText: { color: '#FFF', fontSize: 11, fontWeight: '700' },
  timelineContent: { flex: 1 },
  timelineName: { fontSize: 13, fontWeight: '600', color: colors.textPrimary, marginBottom: 2 },
  timelineDate: { fontSize: 11, color: colors.textMuted, marginBottom: 4 },
  statusPill: { alignSelf: 'flex-start', borderRadius: 8, paddingHorizontal: 7, paddingVertical: 2 },
  statusPillText: { fontSize: 10, fontWeight: '600' },

  letterPreview: {
    backgroundColor: '#FAFAFA',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  letterPreviewTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 6 },
  letterPreviewText:  { fontSize: 11, color: colors.textPrimary, lineHeight: 17 },

  legalBox: { backgroundColor: colors.surfaceAlt, borderRadius: 8, padding: 10, marginBottom: 10 },
  legalText: { fontSize: 11, color: colors.textSecondary },
  disclaimer: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic', textAlign: 'center' },
});
