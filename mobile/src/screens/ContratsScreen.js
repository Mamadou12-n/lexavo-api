import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { listContractTemplates, generateContract } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import { LinearGradient } from 'expo-linear-gradient';

const CONTRACT_BLUE = '#2980B9';

export default function ContratsScreen() {
  const [templates, setTemplates]   = useState([]);
  const [selected, setSelected]     = useState(null);
  const [variables, setVariables]   = useState({});
  const [fetching, setFetching]     = useState(true);
  const [loading, setLoading]       = useState(false);
  const [result, setResult]         = useState(null);
  const [error, setError]           = useState(null);
  const [photos, setPhotos] = useState([]);

  useEffect(() => {
    listContractTemplates()
      .then((d) => setTemplates(d.templates ?? []))
      .catch(() => setTemplates([]))
      .finally(() => setFetching(false));
  }, []);

  const selectTemplate = (t) => {
    setSelected(t);
    setVariables({});
    setResult(null);
    setError(null);
  };

  const generate = async () => {
    if (!selected) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const data = await generateContract(selected.id, variables);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur de génération');
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={CONTRACT_BLUE} size="large" />
        <Text style={styles.loadingText}>Chargement des modèles...</Text>
      </View>
    );
  }

  const fields = selected?.variables ?? [];

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        {/* Template selector */}
        <LinearGradient colors={['#0A1628', '#1A3A5C']} style={styles.heroHeader}>
          <Text style={styles.heroEmoji}>📝</Text>
          <Text style={styles.heroTitle}>Contrats — Génération PDF</Text>
          <Text style={styles.heroSub}>Choisissez un modèle de contrat</Text>
        </LinearGradient>

        <View style={styles.card}>
          {templates.map((t) => (
            <TouchableOpacity activeOpacity={0.75}
              key={t.id}
              style={[styles.templateBtn, selected?.id === t.id && styles.templateBtnActive]}
              onPress={() => selectTemplate(t)}
            >
              <View style={styles.templateRow}>
                <Text style={styles.templateEmoji}>{t.emoji ?? '📄'}</Text>
                <View style={styles.templateInfo}>
                  <Text style={[styles.templateName, selected?.id === t.id && styles.templateNameActive]}>
                    {t.name}
                  </Text>
                  {t.description && (
                    <Text style={styles.templateDesc}>{t.description}</Text>
                  )}
                </View>
                {selected?.id === t.id && (
                  <Text style={styles.checkmark}>✓</Text>
                )}
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* Variables form */}
        {selected && fields.length > 0 && (
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>{selected.name} — Informations</Text>
            {fields.map((f) => (
              <View key={f.key} style={styles.fieldWrap}>
                <Text style={styles.fieldLabel}>{f.label}{f.required ? ' *' : ''}</Text>
                <TextInput
                  style={styles.input}
                  placeholder={f.placeholder ?? f.label}
                  placeholderTextColor={colors.textMuted}
                  value={variables[f.key] ?? ''}
                  onChangeText={(t) => setVariables((v) => ({ ...v, [f.key]: t }))}
                  accessibilityLabel={f.label}
                />
              </View>
            ))}
            <TouchableOpacity activeOpacity={0.75}
              style={[styles.btn, loading && styles.btnDisabled]}
              onPress={generate}
              disabled={loading}
            >
              {loading
                ? <ActivityIndicator color="#FFF" />
                : <Text style={styles.btnText}>📝  Générer le contrat</Text>
              }
            </TouchableOpacity>
          </View>
        )}

        {selected && fields.length === 0 && (
          <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, loading && styles.btnDisabled]}
            onPress={generate}
            disabled={loading}
          >
            {loading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>📝  Générer le contrat</Text>
            }
          </TouchableOpacity>
        )}

        {/* Error */}
        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>⚠️ {error}</Text>
          </View>
        )}

        {/* Preview */}
        {result && (
          <View style={styles.card}>
            <View style={styles.previewHeader}>
              <Text style={styles.previewTitle}>📄 {result.template_name ?? selected?.name}</Text>
              <View style={styles.previewBadge}>
                <Text style={styles.previewBadgeText}>Prêt</Text>
              </View>
            </View>
            {result.preview && (
              <View style={styles.previewBox}>
                <Text style={styles.previewText} numberOfLines={20}>{result.preview}</Text>
              </View>
            )}
            {result.legal_basis && (
              <View style={styles.legalBox}>
                <Text style={styles.legalText}>📖 {result.legal_basis}</Text>
              </View>
            )}
            <View style={{ marginTop: 12, padding: 10, backgroundColor: '#FFFBEB', borderRadius: 8, borderWidth: 1, borderColor: '#FDE68A' }}>
              <Text style={{ fontSize: 10, color: '#92400E', textAlign: 'center', fontStyle: 'italic', lineHeight: 14 }}>
                ⚖️ Lexavo est un outil d'information juridique. Il ne remplace pas un avocat ni un conseiller juridique professionnel.
              </Text>
            </View>
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content:   { padding: 16, paddingBottom: 40 },
  center:    { flex: 1, alignItems: 'center', justifyContent: 'center' },
  loadingText: { marginTop: 12, color: colors.textMuted, fontSize: 13 },

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

  templateBtn: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 12,
    marginBottom: 8,
    backgroundColor: colors.background,
  },
  templateBtnActive: { borderColor: CONTRACT_BLUE, backgroundColor: '#EFF6FF' },
  templateRow:  { flexDirection: 'row', alignItems: 'center', gap: 10 },
  templateEmoji: { fontSize: 20 },
  templateInfo: { flex: 1 },
  templateName: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  templateNameActive: { color: CONTRACT_BLUE },
  templateDesc: { fontSize: 11, color: colors.textMuted, marginTop: 1 },
  checkmark: { fontSize: 16, color: CONTRACT_BLUE, fontWeight: '700' },

  sectionTitle: { fontSize: 13, fontWeight: '700', color: colors.textSecondary, marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.5 },

  fieldWrap: { marginBottom: 12 },
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
    backgroundColor: CONTRACT_BLUE,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 4,
    marginBottom: 4,
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

  previewHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  previewTitle:  { fontSize: 14, fontWeight: '700', color: colors.textPrimary, flex: 1 },
  previewBadge:  { backgroundColor: '#D1FAE5', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3 },
  previewBadgeText: { fontSize: 11, color: '#065F46', fontWeight: '700' },

  previewBox: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  previewText: { fontSize: 12, color: colors.textPrimary, lineHeight: 18, fontFamily: 'monospace' },

  legalBox: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
  },
  legalText:  { fontSize: 11, color: colors.textSecondary },
  disclaimer: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic', textAlign: 'center' },
});
