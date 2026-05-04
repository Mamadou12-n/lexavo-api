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
import { typography, spacing, radius } from '../theme/designSystem';
import { Ionicons } from '@expo/vector-icons';
import { useLanguage } from '../context/LanguageContext';

// Tokens — utiliser colors.brand / colors.brandNavy partout
const LEXAVO_NAVY   = colors.brandNavy;
const LEXAVO_ORANGE = colors.brand;

export default function AuthScreen({ onAuthSuccess }) {
  const { t } = useLanguage();
  const [mode, setMode]         = useState('login');   // 'login' | 'register' | 'forgot'
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [name, setName]         = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [forgotSent, setForgotSent] = useState(false);
  const [focusedField, setFocusedField] = useState(null);

  const isLogin = mode === 'login';
  const isForgot = mode === 'forgot';

  const submitForgot = async () => {
    setError(null);
    const trimEmail = email.trim().toLowerCase();
    if (!trimEmail) { setError(t('auth_err_email_required')); return; }
    setLoading(true);
    try {
      await forgotPassword(trimEmail);
      setForgotSent(true);
    } catch (e) {
      setError(e.response?.data?.detail || t('auth_err_retry'));
    } finally {
      setLoading(false);
    }
  };

  const submit = async () => {
    setError(null);
    const trimEmail = email.trim().toLowerCase();
    const trimPass  = password.trim();

    if (!trimEmail || !trimPass) {
      setError(t('auth_err_creds'));
      return;
    }
    if (trimPass.length < 6) {
      setError(t('auth_err_pass_short'));
      return;
    }
    if (!isLogin && !name.trim()) {
      setError(t('auth_err_name_required'));
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
        t('auth_err_generic');
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
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <Ionicons name="scale-outline" size={28} color="#FFF" accessibilityElementsHidden />
          <Text style={styles.logo}>Lexavo</Text>
        </View>
        <Text style={styles.tagline}>{t('auth_tagline')}</Text>
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
              accessible={true}
              accessibilityRole="tab"
              accessibilityLabel={t('auth_tab_login')}
              accessibilityState={{ selected: isLogin }}
            >
              <Text style={[styles.tabText, isLogin && styles.tabTextActive]}>
                {t('auth_tab_login')}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity activeOpacity={0.75}
              style={[styles.tab, !isLogin && styles.tabActive]}
              onPress={() => { setMode('register'); setError(null); }}
              accessible={true}
              accessibilityRole="tab"
              accessibilityLabel={t('auth_tab_register')}
              accessibilityState={{ selected: !isLogin }}
            >
              <Text style={[styles.tabText, !isLogin && styles.tabTextActive]}>
                {t('auth_tab_register')}
              </Text>
            </TouchableOpacity>
          </View>

          {/* Champ nom (inscription uniquement) */}
          {!isLogin && (
            <View style={styles.field}>
              <Text style={styles.label}>{t('auth_full_name')}</Text>
              <TextInput
                style={[styles.input, focusedField === 'name' && styles.inputFocused]}
                value={name}
                onChangeText={setName}
                onFocus={() => setFocusedField('name')}
                onBlur={() => setFocusedField(null)}
                placeholder="Jean Dupont"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="words"
                autoCorrect={false}
                returnKeyType="next"
                accessibilityLabel={t('auth_full_name')}
              />
            </View>
          )}

          {/* Email */}
          <View style={styles.field}>
            <Text style={styles.label}>{t('auth_email')}</Text>
            <TextInput
              style={[styles.input, focusedField === 'email' && styles.inputFocused]}
              value={email}
              onChangeText={setEmail}
              onFocus={() => setFocusedField('email')}
              onBlur={() => setFocusedField(null)}
              placeholder="votre@email.be"
              placeholderTextColor={colors.textMuted}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="next"
              accessibilityLabel={t('auth_email')}
            />
          </View>

          {/* Mot de passe */}
          <View style={styles.field}>
            <Text style={styles.label}>{t('auth_password')}</Text>
            <TextInput
              style={[styles.input, focusedField === 'password' && styles.inputFocused]}
              value={password}
              onChangeText={setPassword}
              onFocus={() => setFocusedField('password')}
              onBlur={() => setFocusedField(null)}
              placeholder={t('auth_password_hint')}
              placeholderTextColor={colors.textMuted}
              secureTextEntry
              autoCapitalize="none"
              returnKeyType="done"
              onSubmitEditing={submit}
              accessibilityLabel={t('auth_password')}
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
            accessible={true}
            accessibilityRole="button"
            accessibilityLabel={isLogin ? t('auth_login_btn') : t('auth_register_btn')}
          >
            {loading ? (
              <ActivityIndicator color="#FFF" />
            ) : (
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <Ionicons name={isLogin ? 'lock-closed-outline' : 'sparkles-outline'} size={18} color="#FFF" accessibilityElementsHidden />
                <Text style={styles.btnText}>
                  {isLogin ? t('auth_login_btn') : t('auth_register_btn')}
                </Text>
              </View>
            )}
          </TouchableOpacity>

          {/* Lien mot de passe oublié */}
          {isLogin && !isForgot && (
            <TouchableOpacity activeOpacity={0.75} onPress={() => { setMode('forgot'); setError(null); setForgotSent(false); }} accessible={true} accessibilityRole="link" accessibilityLabel={t('auth_forgot')}>
              <Text style={styles.forgotLink}>{t('auth_forgot')}</Text>
            </TouchableOpacity>
          )}

          {/* Vue forgot password */}
          {isForgot && (
            <View style={styles.forgotBox}>
              {forgotSent ? (
                <>
                  <Text style={styles.forgotTitle}>{t('auth_forgot_sent_title')}</Text>
                  <Text style={styles.forgotText}>
                    {t('auth_forgot_sent_text')}
                  </Text>
                  <TouchableOpacity activeOpacity={0.75} onPress={() => { setMode('login'); setForgotSent(false); }} accessible={true} accessibilityRole="link" accessibilityLabel={t('auth_forgot_back')}>
                    <Text style={styles.forgotLink}>{t('auth_forgot_back')}</Text>
                  </TouchableOpacity>
                </>
              ) : (
                <>
                  <Text style={styles.forgotTitle}>{t('auth_forgot_title')}</Text>
                  <View style={styles.field}>
                    <Text style={styles.label}>{t('auth_email')}</Text>
                    <TextInput
                      style={[styles.input, focusedField === 'forgot-email' && styles.inputFocused]}
                      value={email}
                      onChangeText={setEmail}
                      onFocus={() => setFocusedField('forgot-email')}
                      onBlur={() => setFocusedField(null)}
                      placeholder="votre@email.be"
                      placeholderTextColor={colors.textMuted}
                      keyboardType="email-address"
                      autoCapitalize="none"
                      autoCorrect={false}
                      accessibilityLabel={t('auth_email')}
                    />
                  </View>
                  <TouchableOpacity activeOpacity={0.75}
                    style={[styles.btn, loading && styles.btnDisabled]}
                    onPress={submitForgot}
                    disabled={loading}
                    accessible={true}
                    accessibilityRole="button"
                    accessibilityLabel={t('auth_forgot_send')}
                  >
                    {loading ? <ActivityIndicator color="#FFF" /> : <Text style={styles.btnText}>{t('auth_forgot_send')}</Text>}
                  </TouchableOpacity>
                  <TouchableOpacity activeOpacity={0.75} onPress={() => { setMode('login'); setError(null); }} accessible={true} accessibilityRole="link" accessibilityLabel={t('auth_forgot_back')}>
                    <Text style={styles.forgotLink}>{t('auth_forgot_back')}</Text>
                  </TouchableOpacity>
                </>
              )}
            </View>
          )}

          {/* Note plans gratuits */}
          {!isLogin && !isForgot && (
            <Text style={styles.planNote}>{t('auth_plan_note')}</Text>
          )}

          {/* Avertissement légal */}
          <Text style={styles.disclaimer}>{t('auth_legal_note')}</Text>
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
  inputFocused: {
    borderColor: colors.brand,
    borderWidth: 2,
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
