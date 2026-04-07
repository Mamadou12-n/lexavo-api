import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { decodeDocument } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import ModelBadge from '../components/ModelBadge';

const URGENCY_COLOR = { critical: '#E74C3C', high: '#E67E22', medium: '#F39C12', low: '#27AE60' };
const URGENCY_LABEL = { critical: '🚨 Critique', high: '⚠️ Urgent', medium: '📋 Modéré', low: 'ℹ️ Information' };

export default function DecodeScreen() {
  const [docText, setDocText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState(null);
  const [error, setError]     = useState(null);
  const [photos, setPhotos] = useState([]);

  const decode = async () => {
    if (!docText.trim()) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const data = await decodeDocument(docText.trim(), 'fr', photos);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally {
      setLoading(false);
    }
  };

  const urgency = result?.urgency ?? 'low';

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        <View style={styles.card}>
          <View style={styles.featureHeader}>
            <Text style={styles.featureEmoji}>🔍</Text>
            <View>
              <Text style={styles.featureTitle}>Decode — Déchiffrer un document</Text>
              <Text style={styles.featureSub}>Collez le texte de votre lettre ou document juridique</Text>
            </View>
          </View>
          <TextInput
            style={styles.textArea}
            multiline
            numberOfLines={8}
            placeholder="Collez ici le texte d'une lettre recommandée, d'un jugement, d'un avis d'imposition..."
            placeholderTextColor={colors.textMuted}
            value={docText}
            onChangeText={setDocText}
            textAlignVertical="top"
            accessibilityLabel="Texte du document"
          />
          <PhotoPicker photos={photos} onPhotosChange={setPhotos} label="📷 Photo du document" />

          <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, (!docText.trim() || loading) && styles.btnDisabled]}
            onPress={decode}
            disabled={!docText.trim() || loading}
          >
            {loading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>🔍  Décoder ce document</Text>
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
            {/* Urgency banner */}
            <View style={[styles.urgencyBanner, { backgroundColor: URGENCY_COLOR[urgency] }]}>
              <Text style={styles.urgencyText}>{URGENCY_LABEL[urgency] ?? urgency}</Text>
              {result.deadline && (
                <Text style={styles.urgencyDeadline}>Délai : {result.deadline}</Text>
              )}
            </View>

            <ModelBadge model={result.model} />
            {/* Document type */}
            {result.document_type && (
              <View style={styles.typePill}>
                <Text style={styles.typePillText}>
                  📄 {result.document_type.replace(/_/g, ' ')}
                </Text>
              </View>
            )}

            {/* Summary */}
            {result.plain_summary && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>En clair</Text>
                <Text style={styles.bodyText}>{result.plain_summary}</Text>
              </View>
            )}

            {/* Key points */}
            {result.key_points?.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Points clés</Text>
                {result.key_points.map((p, i) => (
                  <View key={i} style={styles.listItem}>
                    <Text style={styles.bullet}>•</Text>
                    <Text style={styles.listText}>{p}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Action required */}
            {result.action_required && (
              <View style={styles.actionBox}>
                <Text style={styles.actionTitle}>➡️  Action requise</Text>
                <Text style={styles.actionText}>{result.action_required}</Text>
              </View>
            )}

            {/* Legal context */}
            {result.legal_context && (
              <View style={styles.legalBox}>
                <Text style={styles.legalText}>📖 {result.legal_context}</Text>
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

  textArea: {
    backgroundColor: colors.background,
    borderRadius: 10,
    padding: 12,
    fontSize: 13,
    color: colors.textPrimary,
    minHeight: 160,
    borderWidth: 1,
    borderColor: colors.border,
    lineHeight: 19,
    marginBottom: 12,
  },
  btn: {
    backgroundColor: '#7B2FBE',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
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

  urgencyBanner: {
    borderRadius: 10,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  urgencyText:     { color: '#FFF', fontSize: 14, fontWeight: '700' },
  urgencyDeadline: { color: 'rgba(255,255,255,0.9)', fontSize: 12, fontWeight: '600' },

  typePill: {
    alignSelf: 'flex-start',
    backgroundColor: colors.surfaceAlt,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginBottom: 12,
  },
  typePillText: { fontSize: 11, color: colors.textSecondary, fontWeight: '600' },

  section:      { marginBottom: 14 },
  sectionTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  bodyText:     { fontSize: 14, color: colors.textPrimary, lineHeight: 21 },

  listItem: { flexDirection: 'row', gap: 8, marginBottom: 6 },
  bullet:   { color: colors.primary, fontWeight: '700', fontSize: 14 },
  listText: { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 19 },

  actionBox: {
    backgroundColor: '#EFF6FF',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#BFDBFE',
    marginBottom: 12,
  },
  actionTitle: { fontSize: 13, fontWeight: '700', color: colors.primary, marginBottom: 4 },
  actionText:  { fontSize: 13, color: colors.textPrimary, lineHeight: 19 },

  legalBox: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
  },
  legalText: { fontSize: 11, color: colors.textSecondary, lineHeight: 16 },

  disclaimer: {
    fontSize: 10,
    color: colors.textMuted,
    fontStyle: 'italic',
    textAlign: 'center',
    lineHeight: 14,
  },
});
