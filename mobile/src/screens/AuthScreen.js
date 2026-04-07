/**
 * AuthScreen — Lexavo
 * Écran de connexion / inscription.
 * Appelé au démarrage si aucun JWT n'est stocké.
 */

import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, TouchableOpacity,
  KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator,
  Alert, StatusBar,
} from 'react-native';
import { login, register, forgotPassword } from '../api/client';
import { colors } from '../theme/colors';

const LEXAVO_NAVY   = '#1C2B3A';
const LEXAVO_ORANGE = '#C45A2D';

export default function AuthScreen({ onAuthSuccess }) {
  const [mode, setMode]         = useState('login');   // 'login' | 'register' | 'forgot'
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [name, setName]         = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [forgotSent, setForgotSent] = useState(false);

  const isLogin = mode === 'login';
  const isForgot = mode === 'forgot';

  const submitForgot = async () => {
    setError(null);
    const trimEmail = email.trim().toLowerCase();
    if (!trimEmail) { setError('Entrez votre adresse email.'); return; }
    setLoading(true);
    try {
      await forgotPassword(trimEmail);
      setForgotSent(true);
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur. Réessayez.');
    } finally {
      setLoading(false);
    }
  };

  const submit = async () => {
    setError(null);
    const trimEmail = email.trim().toLowerCase();
    const trimPass  = password.trim();

    if (!trimEmail || !trimPass) {
      setError('Email et mot de passe obligatoires.');
      return;
    }
    if (trimPass.length < 6) {
      setError('Le mot de passe doit faire au moins 6 caractères.');
      return;
    }
    if (!isLogin && !name.trim()) {
      setError('Le nom est obligatoire pour l\'inscription.');
      return;
    }

    setLoading(true);
    try {
      if (isLogin) {
        await login(trimEmail, trimPass);
      } else {
        await register(trimEmail, trimPass, name.trim());
      }
      onAuthSuccess();
    } catch (e) {
      const msg =
        e.response?.data?.detail ||
        e.response?.data?.message ||
        e.message ||
        'Une erreur est survenue. Vérifiez votre connexion.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={LEXAVO_NAVY} />

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.logo}>⚖️  Lexavo</Text>
        <Text style={styles.tagline}>Droit belge — RAG + IA</Text>
      </View>

      {/* Card */}
      <KeyboardAvoidingView
        style={styles.cardWrap}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          contentContainerStyle={styles.card}
          keyboardShouldPersistTaps="handled"
        >
          {/* Onglets login / inscription */}
          <View style={styles.tabs}>
            <TouchableOpacity activeOpacity={0.75}
              style={[styles.tab, isLogin && styles.tabActive]}
              onPress={() => { setMode('login'); setError(null); }}
            >
              <Text style={[styles.tabText, isLogin && styles.tabTextActive]}>
                Connexion
              </Text>
            </TouchableOpacity>
            <TouchableOpacity activeOpacity={0.75}
              style={[styles.tab, !isLogin && styles.tabActive]}
              onPress={() => { setMode('register'); setError(null); }}
            >
              <Text style={[styles.tabText, !isLogin && styles.tabTextActive]}>
                Inscription
              </Text>
            </TouchableOpacity>
          </View>

          {/* Champ nom (inscription uniquement) */}
          {!isLogin && (
            <View style={styles.field}>
              <Text style={styles.label}>Nom complet</Text>
              <TextInput
                style={styles.input}
                value={name}
                onChangeText={setName}
                placeholder="Jean Dupont"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="words"
                autoCorrect={false}
                returnKeyType="next"
                accessibilityLabel="Nom complet"
              />
            </View>
          )}

          {/* Email */}
          <View style={styles.field}>
            <Text style={styles.label}>Adresse email</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="votre@email.be"
              placeholderTextColor={colors.textMuted}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="next"
              accessibilityLabel="Adresse email"
            />
          </View>

          {/* Mot de passe */}
          <View style={styles.field}>
            <Text style={styles.label}>Mot de passe</Text>
            <TextInput
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder="Min. 6 caractères"
              placeholderTextColor={colors.textMuted}
              secureTextEntry
              autoCapitalize="none"
              returnKeyType="done"
              onSubmitEditing={submit}
              accessibilityLabel="Mot de passe"
            />
          </View>

          {/* Erreur */}
          {error && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {/* Bouton */}
          <TouchableOpacity activeOpacity={0.75}
            style={[styles.btn, loading && styles.btnDisabled]}
            onPress={submit}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#FFF" />
            ) : (
              <Text style={styles.btnText}>
                {isLogin ? '🔐 Se connecter' : '✨ Créer mon compte'}
              </Text>
            )}
          </TouchableOpacity>

          {/* Lien mot de passe oublié */}
          {isLogin && !isForgot && (
            <TouchableOpacity activeOpacity={0.75} onPress={() => { setMode('forgot'); setError(null); setForgotSent(false); }}>
              <Text style={styles.forgotLink}>Mot de passe oublié ?</Text>
            </TouchableOpacity>
          )}

          {/* Vue forgot password */}
          {isForgot && (
            <View style={styles.forgotBox}>
              {forgotSent ? (
                <>
                  <Text style={styles.forgotTitle}>Email envoyé ✓</Text>
                  <Text style={styles.forgotText}>
                    Si un compte existe avec cet email, vous recevrez un lien de réinitialisation.
                  </Text>
                  <TouchableOpacity activeOpacity={0.75} onPress={() => { setMode('login'); setForgotSent(false); }}>
                    <Text style={styles.forgotLink}>← Retour à la connexion</Text>
                  </TouchableOpacity>
                </>
              ) : (
                <>
                  <Text style={styles.forgotTitle}>Réinitialiser le mot de passe</Text>
                  <View style={styles.field}>
                    <Text style={styles.label}>Adresse email</Text>
                    <TextInput
                      style={styles.input}
                      value={email}
                      onChangeText={setEmail}
                      placeholder="votre@email.be"
                      placeholderTextColor={colors.textMuted}
                      keyboardType="email-address"
                      autoCapitalize="none"
                      autoCorrect={false}
                      accessibilityLabel="Adresse email"
                    />
                  </View>
                  <TouchableOpacity activeOpacity={0.75}
                    style={[styles.btn, loading && styles.btnDisabled]}
                    onPress={submitForgot}
                    disabled={loading}
                  >
                    {loading ? <ActivityIndicator color="#FFF" /> : <Text style={styles.btnText}>Envoyer le lien</Text>}
                  </TouchableOpacity>
                  <TouchableOpacity activeOpacity={0.75} onPress={() => { setMode('login'); setError(null); }}>
                    <Text style={styles.forgotLink}>← Retour à la connexion</Text>
                  </TouchableOpacity>
                </>
              )}
            </View>
          )}

          {/* Note plans gratuits */}
          {!isLogin && !isForgot && (
            <Text style={styles.planNote}>
              Compte gratuit : 5 questions/mois incluses.{'\n'}
              Passez au plan Pro (29€/mois) depuis les Réglages.
            </Text>
          )}

          {/* Avertissement légal */}
          <Text style={styles.disclaimer}>
            🇧🇪 Lexavo fournit une aide à la recherche juridique.
            Les réponses ne constituent pas un conseil juridique professionnel.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: LEXAVO_NAVY },

  header: {
    alignItems: 'center',
    paddingTop: Platform.OS === 'ios' ? 70 : 50,
    paddingBottom: 30,
  },
  logo: {
    fontSize: 28,
    fontWeight: '800',
    color: '#FFF',
    letterSpacing: 0.5,
  },
  tagline: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.6)',
    marginTop: 6,
  },

  cardWrap: { flex: 1 },
  card: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    paddingBottom: 40,
    flexGrow: 1,
  },

  tabs: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceAlt,
    borderRadius: 12,
    padding: 4,
    marginBottom: 24,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 10,
  },
  tabActive: {
    backgroundColor: LEXAVO_NAVY,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  tabTextActive: {
    color: '#FFF',
  },

  field: { marginBottom: 16 },
  label: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.textSecondary,
    textTransform: 'uppercase',
    marginBottom: 6,
    letterSpacing: 0.4,
  },
  input: {
    backgroundColor: colors.background,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.border,
  },

  errorBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#FCA5A5',
  },
  errorText: {
    fontSize: 13,
    color: colors.error,
    fontWeight: '500',
  },

  btn: {
    backgroundColor: LEXAVO_ORANGE,
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: 'center',
    marginBottom: 16,
    elevation: 3,
    shadowColor: LEXAVO_ORANGE,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 0.3,
  },

  planNote: {
    fontSize: 12,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: 16,
  },
  disclaimer: {
    fontSize: 11,
    color: colors.textMuted,
    textAlign: 'center',
    lineHeight: 16,
    marginTop: 8,
  },

  forgotLink: {
    color: LEXAVO_ORANGE,
    fontSize: 13,
    textAlign: 'center',
    marginBottom: 16,
    textDecorationLine: 'underline',
  },
  forgotBox: {
    marginTop: 8,
  },
  forgotTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: LEXAVO_NAVY,
    marginBottom: 12,
    textAlign: 'center',
  },
  forgotText: {
    fontSize: 13,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 16,
  },
});
