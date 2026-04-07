import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform, Linking,
} from 'react-native';
import { getEmergencyCategories, createEmergencyRequest } from '../api/client';
import { colors } from '../theme/colors';
import PhotoPicker from '../components/PhotoPicker';
import { LinearGradient } from 'expo-linear-gradient';

const EMERGENCY_RED = '#E74C3C';

export default function EmergencyScreen() {
  const [categories, setCategories] = useState([]);
  const [category, setCategory]     = useState(null);
  const [description, setDesc]      = useState('');
  const [email, setEmail]           = useState('');
  const [fetching, setFetching]     = useState(true);
  const [loading, setLoading]       = useState(false);
  const [result, setResult]         = useState(null);
  const [error, setError]           = useState(null);
  const [photos, setPhotos] = useState([]);

  useEffect(() => {
    getEmergencyCategories()
      .then((d) => setCategories(d.categories ?? []))
      .catch(() => {})
      .finally(() => setFetching(false));
  }, []);

  const submit = async () => {
    if (!category || !description.trim() || !email.trim()) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const data = await createEmergencyRequest(category.id, description.trim(), email.trim(), '', photos);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={EMERGENCY_RED} size="large" />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        {/* Warning banner */}
        <LinearGradient colors={['#7C1D1D', '#E74C3C']} style={styles.heroHeader}>
          <Text style={styles.heroEmoji}>🚨</Text>
          <Text style={styles.heroTitle}>Service d'urgence juridique</Text>
          <Text style={styles.heroSub}>Réponse garantie dans les 24 heures — 49€</Text>
        </LinearGradient>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Type d'urgence</Text>
          {categories.map((c) => (
            <TouchableOpacity activeOpacity={0.75}
              key={c.id}
              style={[styles.catBtn, category?.id === c.id && styles.catBtnActive]}
              onPress={() => setCategory(c)}
            >
              <Text style={styles.catEmoji}>{c.emoji ?? '⚠️'}</Text>
              <View style={styles.catInfo}>
                <Text style={[styles.catName, category?.id === c.id && styles.catNameActive]}>
                  {c.name}
                </Text>
                {c.description && (
                  <Text style={styles.catDesc}>{c.description}</Text>
                )}
              </View>
              {category?.id === c.id && (
                <Text style={styles.catCheck}>✓</Text>
              )}
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Décrivez votre urgence</Text>
          <TextInput
            style={styles.textArea}
            multiline
            numberOfLines={5}
            placeholder="Décrivez votre situation d'urgence juridique en détail..."
            placeholderTextColor={colors.textMuted}
            value={description}
            onChangeText={setDesc}
            textAlignVertical="top"
            accessibilityLabel="Description de l'urgence"
          />
          <Text style={[styles.sectionTitle, { marginTop: 12 }]}>Votre email</Text>
          <TextInput
            style={styles.input}
            placeholder="votre@email.be"
            placeholderTextColor={colors.textMuted}
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            accessibilityLabel="Adresse email"
          />

          {/* Price block */}
          <View style={styles.priceBox}>
            <Text style={styles.priceLabel}>Tarif urgence juridique</Text>
            <Text style={styles.priceValue}>49€</Text>
            <Text style={styles.priceNote}>Réponse d'avocat sous 24h · 100% remboursé si non répondu</Text>
          </View>

          <PhotoPicker photos={photos} onPhotosChange={setPhotos} />

            <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, (!category || !description.trim() || !email.trim() || loading) && styles.btnDisabled]}
            onPress={submit}
            disabled={!category || !description.trim() || !email.trim() || loading}
          >
            {loading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.btnText}>🚨  Envoyer l'urgence — 49€</Text>
            }
          </TouchableOpacity>
        </View>

        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>⚠️ {error}</Text>
          </View>
        )}

        {result && (
          <View style={[styles.card, styles.confirmCard]}>
            <Text style={styles.confirmEmoji}>✅</Text>
            <Text style={styles.confirmTitle}>Urgence enregistrée</Text>
            <Text style={styles.confirmId}>Réf. : {result.request_id ?? 'EMG-XXXX'}</Text>

            {result.checkout_url && (
              <TouchableOpacity activeOpacity={0.75}
                style={styles.payBtn}
                onPress={() => Linking.openURL(result.checkout_url)}
              >
                <Text style={styles.payBtnText}>💳 Payer 49€ et confirmer</Text>
              </TouchableOpacity>
            )}

            {result.next_steps?.length > 0 && (
              <View style={styles.stepsSection}>
                <Text style={styles.stepsTitle}>Prochaines étapes</Text>
                {result.next_steps.map((s, i) => (
                  <View key={i} style={styles.stepItem}>
                    <Text style={styles.stepNum}>{i + 1}</Text>
                    <Text style={styles.stepText}>{s}</Text>
                  </View>
                ))}
              </View>
            )}

            {result.response_time && (
              <Text style={styles.responseTime}>⏱ Délai garanti : {result.response_time}</Text>
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
  sectionTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 },

  catBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 12,
    marginBottom: 8,
    backgroundColor: colors.background,
  },
  catBtnActive: { borderColor: EMERGENCY_RED, backgroundColor: '#FEF2F2' },
  catEmoji:  { fontSize: 20 },
  catInfo:   { flex: 1 },
  catName:   { fontSize: 13, fontWeight: '600', color: colors.textPrimary },
  catNameActive: { color: EMERGENCY_RED },
  catDesc:   { fontSize: 11, color: colors.textMuted, marginTop: 1 },
  catCheck:  { fontSize: 16, color: EMERGENCY_RED, fontWeight: '700' },

  textArea: {
    backgroundColor: colors.background,
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    color: colors.textPrimary,
    minHeight: 110,
    borderWidth: 1,
    borderColor: colors.border,
    lineHeight: 20,
    marginBottom: 10,
  },
  input: {
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: 10,
    fontSize: 14,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 12,
  },

  priceBox: {
    backgroundColor: '#FFF7ED',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#FED7AA',
  },
  priceLabel: { fontSize: 11, color: '#92400E', marginBottom: 2 },
  priceValue: { fontSize: 28, fontWeight: '900', color: '#D97706' },
  priceNote:  { fontSize: 10, color: '#92400E', textAlign: 'center', marginTop: 2 },

  btn: {
    backgroundColor: EMERGENCY_RED,
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

  confirmCard:  { alignItems: 'center', borderWidth: 2, borderColor: '#BBF7D0' },
  confirmEmoji: { fontSize: 40, marginBottom: 8 },
  confirmTitle: { fontSize: 18, fontWeight: '800', color: '#065F46', marginBottom: 4 },
  confirmId:    { fontSize: 13, color: colors.textMuted, fontFamily: 'monospace', marginBottom: 12 },
  payBtn:       { backgroundColor: EMERGENCY_RED, borderRadius: 12, paddingVertical: 14, paddingHorizontal: 24, marginBottom: 16, alignSelf: 'stretch', alignItems: 'center' },
  payBtnText:   { color: '#FFF', fontSize: 16, fontWeight: '700' },

  stepsSection: { width: '100%', marginBottom: 10 },
  stepsTitle: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 8, textTransform: 'uppercase' },
  stepItem: { flexDirection: 'row', gap: 8, marginBottom: 6, alignItems: 'flex-start' },
  stepNum: {
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: '#27AE60',
    color: '#FFF',
    fontSize: 10,
    fontWeight: '700',
    textAlign: 'center',
    lineHeight: 18,
  },
  stepText: { flex: 1, fontSize: 12, color: colors.textPrimary, lineHeight: 18 },

  responseTime: { fontSize: 12, color: '#065F46', fontWeight: '600' },
});
