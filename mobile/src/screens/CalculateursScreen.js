import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { listCalculators, runCalculator } from '../api/client';
import { colors } from '../theme/colors';
import { LinearGradient } from 'expo-linear-gradient';

const CALC_COLOR = '#27AE60';

// Champs par type de calculateur
const CALC_FIELDS = {
  preavis: [
    { key: 'years', label: "Années d'ancienneté", placeholder: '5', keyboardType: 'numeric' },
    { key: 'monthly_salary', label: 'Salaire mensuel brut (€)', placeholder: '3500', keyboardType: 'numeric' },
  ],
  pension_alimentaire: [
    { key: 'income_high', label: 'Revenu mensuel le plus élevé (€)', placeholder: '4000', keyboardType: 'numeric' },
    { key: 'income_low', label: 'Revenu mensuel le plus bas (€)', placeholder: '1500', keyboardType: 'numeric' },
    { key: 'children', label: "Nombre d'enfants", placeholder: '2', keyboardType: 'numeric' },
  ],
  droits_succession: [
    { key: 'estate_value', label: 'Valeur du patrimoine (€)', placeholder: '250000', keyboardType: 'numeric' },
    { key: 'region', label: 'Région (bruxelles/wallonie/flandre)', placeholder: 'bruxelles' },
    { key: 'relationship', label: 'Lien (enfant/conjoint/autre)', placeholder: 'enfant' },
  ],
};

export default function CalculateursScreen() {
  const [calcList, setCalcList] = useState([]);
  const [selected, setSelected] = useState(null);
  const [values, setValues]     = useState({});
  const [loading, setLoading]   = useState(false);
  const [fetching, setFetching] = useState(true);
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState(null);
  useEffect(() => {
    listCalculators()
      .then((d) => setCalcList(d.calculators ?? []))
      .catch(() => setCalcList([]))
      .finally(() => setFetching(false));
  }, []);

  const selectCalc = (calc) => {
    setSelected(calc);
    setValues({});
    setResult(null);
    setError(null);
  };

  const calculate = async () => {
    if (!selected) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const params = {};
      const fields = CALC_FIELDS[selected.id] ?? [];
      fields.forEach((f) => {
        const v = values[f.key];
        if (v !== undefined && v !== '') {
          params[f.key] = f.keyboardType === 'numeric' ? parseFloat(v) : v;
        }
      });
      const data = await runCalculator(selected.id, params);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur de calcul');
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={CALC_COLOR} size="large" />
        <Text style={styles.loadingText}>Chargement des calculateurs...</Text>
      </View>
    );
  }

  const fields = selected ? (CALC_FIELDS[selected.id] ?? []) : [];

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        {/* Selector */}
        <LinearGradient colors={['#0A3D5C', '#1A6B8A']} style={styles.heroHeader}>
          <Text style={styles.heroEmoji}>🧮</Text>
          <Text style={styles.heroTitle}>Calculateurs juridiques</Text>
          <Text style={styles.heroSub}>Sélectionnez un calcul</Text>
        </LinearGradient>

        <View style={styles.card}>
          <View style={styles.calcList}>
            {calcList.map((c) => (
              <TouchableOpacity activeOpacity={0.75}
                key={c.id}
                style={[styles.calcChip, selected?.id === c.id && styles.calcChipActive]}
                onPress={() => selectCalc(c)}
              >
                <Text style={[styles.calcChipText, selected?.id === c.id && styles.calcChipTextActive]}>
                  {c.emoji ?? '📐'} {c.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Dynamic form */}
        {selected && fields.length > 0 && (
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>{selected.name}</Text>
            {selected.description && (
              <Text style={styles.calcDesc}>{selected.description}</Text>
            )}
            {fields.map((f) => (
              <View key={f.key} style={styles.fieldWrap}>
                <Text style={styles.fieldLabel}>{f.label}</Text>
                <TextInput
                  style={styles.input}
                  placeholder={f.placeholder}
                  placeholderTextColor={colors.textMuted}
                  keyboardType={f.keyboardType ?? 'default'}
                  value={values[f.key] ?? ''}
                  onChangeText={(t) => setValues((v) => ({ ...v, [f.key]: t }))}
                />
              </View>
            ))}
            <TouchableOpacity activeOpacity={0.75}
              style={[styles.btn, loading && styles.btnDisabled]}
              onPress={calculate}
              disabled={loading}
            >
              {loading
                ? <ActivityIndicator color="#FFF" />
                : <Text style={styles.btnText}>🧮  Calculer</Text>
              }
            </TouchableOpacity>
          </View>
        )}

        {/* Error */}
        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>⚠️ {error}</Text>
          </View>
        )}

        {/* Result */}
        {result && (
          <View style={styles.card}>
            {/* Main result */}
            {result.result != null && (
              <View style={styles.resultBox}>
                <Text style={styles.resultLabel}>Résultat</Text>
                <Text style={styles.resultValue}>
                  {typeof result.result === 'number'
                    ? result.result.toLocaleString('fr-BE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                    : String(result.result)}
                  {result.unit ? ` ${result.unit}` : ''}
                </Text>
              </View>
            )}

            {/* Details */}
            {result.details && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Détail du calcul</Text>
                {Object.entries(result.details).map(([k, v]) => (
                  <View key={k} style={styles.detailRow}>
                    <Text style={styles.detailKey}>{k.replace(/_/g, ' ')}</Text>
                    <Text style={styles.detailVal}>{typeof v === 'number' ? v.toLocaleString('fr-BE') : String(v)}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Legal basis */}
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

  calcList: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  calcChip: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.background,
  },
  calcChipActive:     { backgroundColor: CALC_COLOR, borderColor: CALC_COLOR },
  calcChipText:       { fontSize: 12, color: colors.textSecondary },
  calcChipTextActive: { color: '#FFF', fontWeight: '700' },

  sectionTitle: { fontSize: 13, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  calcDesc:     { fontSize: 13, color: colors.textMuted, marginBottom: 12, lineHeight: 18 },

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
    backgroundColor: CALC_COLOR,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 4,
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

  resultBox: {
    backgroundColor: '#F0FDF4',
    borderRadius: 10,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#BBF7D0',
    marginBottom: 14,
  },
  resultLabel: { fontSize: 12, color: '#065F46', fontWeight: '600', marginBottom: 4 },
  resultValue: { fontSize: 28, fontWeight: '800', color: CALC_COLOR },

  section: { marginBottom: 14 },
  detailRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4, borderBottomWidth: 1, borderBottomColor: colors.border },
  detailKey: { fontSize: 12, color: colors.textSecondary, flex: 1 },
  detailVal: { fontSize: 12, fontWeight: '600', color: colors.textPrimary },

  legalBox: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
  },
  legalText: { fontSize: 11, color: colors.textSecondary },
  disclaimer: { fontSize: 10, color: colors.textMuted, fontStyle: 'italic', textAlign: 'center' },
});
