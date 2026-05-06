import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform, Linking,
  Animated, Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import Markdown from 'react-native-markdown-display';
import { askQuestion, SOURCES, getSubscriptionStatus } from '../api/client';
import { colors, sourceColor } from '../theme/colors';
import { typography, spacing, radius, elevation } from '../theme/designSystem';
import { Ionicons } from '@expo/vector-icons';
import SourceBadge from '../components/SourceBadge';
import PhotoPicker from '../components/PhotoPicker';
import { Disclaimer } from '../components/ui/Disclaimer';
import { useLanguage } from '../context/LanguageContext';
import {
  QuotaBanner,
  QuotaWarningModal,
  QuotaBlockedModal,
  useQuotaStatus,
} from '../components/quota';

const SUGGESTED_KEYS = ['ask_q1', 'ask_q2', 'ask_q3', 'ask_q4', 'ask_q5', 'ask_q6'];

export default function AskScreen() {
  const navigation = useNavigation();
  const { t } = useLanguage();
  const [question, setQuestion] = useState('');
  const [inputFocused, setInputFocused] = useState(false);
  const [answer, setAnswer]     = useState(null);
  const [sources, setSources]   = useState([]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [sourceFilter, setSourceFilter] = useState(null);
  const [showFilters, setShowFilters]   = useState(false);
  const [usedModel, setUsedModel] = useState(null); // modèle retourné par le backend
  const [photos, setPhotos] = useState([]);
  const [quota, setQuota] = useState(null);
  const quotaStatus = useQuotaStatus();
  const goSubscription = () => navigation.navigate('Subscription');
  const scrollRef = useRef(null);
  const fadeAnim  = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    let mounted = true;
    getSubscriptionStatus()
      .then(data => { if (mounted) setQuota(data); })
      .catch(() => {});
    return () => { mounted = false; };
  }, []);

  const submit = async (q = question) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    if (quota && quota.questions_limit > 0 && quota.questions_used >= quota.questions_limit) {
      Alert.alert(t('ask_quota_reached_title'), t('ask_quota_reached_msg'), [
        { text: t('ask_later') },
        { text: t('ask_view_plans'), onPress: () => navigation.navigate('Subscription') },
      ]);
      return;
    }
    setQuestion(trimmed);
    setAnswer(null);
    setSources([]);
    setError(null);
    setLoading(true);

    try {
      const result = await askQuestion(trimmed, {
        top_k: 6,
        source_filter: sourceFilter,
        photos,
      });
      setAnswer(result.answer);
      setSources(result.sources ?? []);
      setUsedModel(result.model ?? null);

      // Scroll + fade in
      setTimeout(() => scrollRef.current?.scrollTo({ y: 0, animated: true }), 100);
      Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    } catch (e) {
      if (e.response?.status === 503) {
        const detail = e.response.data?.detail ?? '';
        if (detail.includes('ANTHROPIC_API_KEY')) {
          setError('Clé API Anthropic manquante.\nConfigurez ANTHROPIC_API_KEY dans le fichier .env du backend.');
        } else if (detail.includes('Index')) {
          setError('L\'index ChromaDB est vide.\nLancez d\'abord :\npython run_all.py --phase indexing');
        } else {
          setError(detail || 'Service indisponible');
        }
      } else {
        setError(e.message || t('ask_error_network'));
      }
    } finally {
      setLoading(false);
    }
  };

  const resetFade = () => fadeAnim.setValue(0);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView
        ref={scrollRef}
        style={styles.scroll}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        {/* Hero Header — fond navy solid, /quieter : ZÉRO LinearGradient décoratif */}
        <View style={styles.heroHeader}>
          <Ionicons
            name="scale-outline"
            size={32}
            color={colors.brand}
            style={{ marginBottom: 8 }}
            accessibilityElementsHidden={true}
          />
          <Text style={styles.heroTitle}>{t('ask_hero_title')}</Text>
          <Text style={styles.heroSub}>{t('ask_hero_sub')}</Text>
        </View>

        {/* Paywall progressif — bandeau awareness selon warning_level */}
        <QuotaBanner status={quotaStatus.status} onPress={goSubscription} />

        {/* Zone de saisie */}
        <View style={styles.inputCard}>
          <Text style={styles.inputLabel}>{t('ask_input_label')}</Text>
          <TextInput
            style={[styles.textArea, inputFocused && styles.textAreaFocused]}
            multiline
            numberOfLines={4}
            placeholder={t('ask_placeholder')}
            placeholderTextColor={colors.textMuted}
            value={question}
            onChangeText={(val) => { setQuestion(val); resetFade(); }}
            onFocus={() => setInputFocused(true)}
            onBlur={() => setInputFocused(false)}
            textAlignVertical="top"
            accessibilityLabel={t('ask_input_label')}
          />

          {/* Filtres source */}
          <TouchableOpacity activeOpacity={0.75}
            style={styles.filterToggle}
            onPress={() => setShowFilters(!showFilters)}
            accessible={true}
            accessibilityRole="button"
            accessibilityLabel={showFilters ? 'Masquer les filtres avancés' : 'Afficher les filtres avancés'}
          >
            <Text style={styles.filterToggleText}>
              {showFilters ? '▲' : '▼'} {t('ask_filters_show')}
              {sourceFilter ? ` — ${sourceFilter}` : ''}
            </Text>
          </TouchableOpacity>

          {showFilters && (
            <View style={styles.filtersPanel}>
              <Text style={styles.filterLabel}>{t('ask_filter_by_source')}</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterScroll}>
                {SOURCES.slice(0, 8).map((s) => (
                  <TouchableOpacity activeOpacity={0.75}
                    key={s.key ?? 'all'}
                    style={[
                      styles.filterChip,
                      sourceFilter === s.key && styles.filterChipActive,
                    ]}
                    onPress={() => setSourceFilter(s.key)}
                    accessible={true}
                    accessibilityRole="button"
                    accessibilityLabel={`Filtrer par source ${s.label}`}
                    accessibilityState={{ selected: sourceFilter === s.key }}
                  >
                    <Text style={[
                      styles.filterChipText,
                      sourceFilter === s.key && styles.filterChipTextActive,
                    ]}>
                      {s.emoji} {s.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>
          )}

          <PhotoPicker photos={photos} onPhotosChange={setPhotos} label={t('ask_attach')} />

          {quota && quota.questions_limit > 0 && (
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 4, marginBottom: 8 }}>
              <Text style={{ fontSize: 11, color: '#64748B' }}>
                {quota.questions_used}/{quota.questions_limit} {t('ask_quota_month')}
              </Text>
              {quota.questions_used >= quota.questions_limit && (
                <TouchableOpacity activeOpacity={0.75} onPress={() => navigation.navigate('Subscription')} accessible={true} accessibilityRole="link" accessibilityLabel={t('ask_upgrade_pro')}>
                  <Text style={{ fontSize: 11, color: colors.brand, fontWeight: '700' }}>{t('ask_upgrade_pro')}</Text>
                </TouchableOpacity>
              )}
            </View>
          )}

          <TouchableOpacity
            style={[styles.submitBtn, (!question.trim() || loading) && styles.submitBtnDisabled]}
            onPress={() => submit()}
            disabled={!question.trim() || loading}
            activeOpacity={0.8}
            accessible={true}
            accessibilityRole="button"
            accessibilityLabel="Analyser ma question juridique"
          >
            {loading
              ? <ActivityIndicator color="#FFF" />
              : <Text style={styles.submitText}>{t('ask_submit')}</Text>
            }
          </TouchableOpacity>
        </View>

        {/* Suggestions */}
        {!answer && !loading && (
          <View style={styles.suggestSection}>
            <Text style={styles.suggestTitle}>{t('ask_suggested_title')}</Text>
            {SUGGESTED_KEYS.map((qk) => {
              const q = t(qk);
              return (
                <TouchableOpacity
                  key={qk}
                  style={styles.suggestItem}
                  onPress={() => { setQuestion(q); submit(q); }}
                  activeOpacity={0.7}
                  accessible={true}
                  accessibilityRole="button"
                  accessibilityLabel={q}
                >
                  <Text style={styles.suggestArrow}>›</Text>
                  <Text style={styles.suggestText}>{q}</Text>
                </TouchableOpacity>
              );
            })}
          </View>
        )}

        {/* Erreur */}
        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorTitle}>{t('ask_error_title')}</Text>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {/* Réponse */}
        {answer && (
          <Animated.View style={[styles.answerCard, { opacity: fadeAnim }]}>
            <View style={styles.answerHeader}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <Ionicons name="scale-outline" size={16} color="#1F2937" />
                <Text style={styles.answerHeaderText}>{t('ask_answer_header')}</Text>
              </View>
            </View>

            <View style={styles.markdownContainer}>
              <Markdown style={markdownStyles}>{answer}</Markdown>
            </View>

            {/* Sources citées */}
            {sources.length > 0 && (
              <View style={styles.sourcesSection}>
                <Text style={styles.sourcesTitle}>
                  {sources.length} {sources.length > 1 ? t('ask_sources_many') : t('ask_sources_one')}
                </Text>
                {sources.map((s, i) => (
                  <SourceCitation key={i} source={s} index={i + 1} />
                ))}
              </View>
            )}

            {/* Disclaimer — composant unique /polish, jamais dupliqué */}
            <View style={styles.answerDisclaimer}>
              <Disclaimer />
            </View>
          </Animated.View>
        )}

        {/* Disclaimer global — /polish : 1 seule instance (pas de doublon) */}
        {!answer && (
          <View style={styles.globalDisclaimer}>
            <Disclaimer />
          </View>
        )}
      </ScrollView>

      {/* Paywall progressif — modals incitation (80%) + blocage (100%) */}
      <QuotaWarningModal
        visible={quotaStatus.showWarningModal}
        status={quotaStatus.status}
        onUpgrade={() => { quotaStatus.setShowWarningModal(false); goSubscription(); }}
        onDismiss={() => quotaStatus.setShowWarningModal(false)}
      />
      <QuotaBlockedModal
        visible={quotaStatus.showBlockedModal}
        status={quotaStatus.status}
        onUpgrade={() => { quotaStatus.setShowBlockedModal(false); goSubscription(); }}
        onClose={() => quotaStatus.setShowBlockedModal(false)}
      />
    </KeyboardAvoidingView>
  );
}

function SourceCitation({ source, index }) {
  const handleUrl = () => {
    if (source.url) Linking.openURL(source.url).catch(() => {});
  };

  return (
    <View style={styles.citation}>
      <View style={styles.citationHeader}>
        <View style={[styles.citationNum, { backgroundColor: sourceColor(source.source) }]}>
          <Text style={styles.citationNumText}>{index}</Text>
        </View>
        <SourceBadge source={source.source || ''} small />
        {source.similarity != null && (
          <Text style={styles.citationSim}>
            {(source.similarity * 100).toFixed(0)}%
          </Text>
        )}
      </View>
      {source.title ? (
        <Text style={styles.citationTitle} numberOfLines={2}>{source.title}</Text>
      ) : null}
      {source.ecli ? (
        <Text style={styles.citationEcli}>{source.ecli}</Text>
      ) : null}
      {source.date ? (
        <Text style={styles.citationDate}>{source.date.slice(0, 10)}</Text>
      ) : null}
      {source.url ? (
        <TouchableOpacity activeOpacity={0.75} onPress={handleUrl} accessible={true} accessibilityRole="link" accessibilityLabel={`Ouvrir la source ${source.url}`}>
          <Text style={styles.citationUrl} numberOfLines={1}>{source.url}</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  scroll:    { flex: 1 },
  content:   { padding: 16, paddingBottom: 40 },

  // Hero — fond navy solid (/quieter : ZÉRO LinearGradient)
  heroHeader: {
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.base,
    alignItems: 'center',
    backgroundColor: colors.brandNavy,
  },
  heroTitle: {
    fontFamily: typography.fontDisplay,
    fontSize: typography.sizeH1,
    color: colors.textOnNavy,
    letterSpacing: 0.5,
  },
  heroSub: {
    fontFamily: typography.fontBody,
    fontSize: typography.sizeCaption,
    // /web-design-guidelines : 0.6→0.80 (WCAG AA)
    color: 'rgba(255,255,255,0.80)',
    marginTop: spacing.xs,
    textAlign: 'center',
  },
  globalDisclaimer: { marginTop: spacing.md },

  inputCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    elevation: 3,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 1,
  },
  inputLabel: {
    fontFamily: typography.fontBodyBold,
    fontSize: typography.sizeCaption,
    color: colors.textSecondary,
    marginBottom: spacing.sm,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
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
  },
  textAreaFocused: {
    borderColor: colors.brand,
    borderWidth: 2,
  },

  filterToggle: { marginTop: 8, alignSelf: 'flex-start', minHeight: 44, justifyContent: 'center' },
  filterToggleText: { fontFamily: typography.fontBodySemiBold, fontSize: typography.sizeCaption, color: colors.brand },
  filtersPanel: { marginTop: 8 },
  filterLabel: { fontSize: 11, color: colors.textMuted, marginBottom: 6 },
  filterScroll: { marginBottom: 8 },
  filterChip: {
    paddingHorizontal: 12, paddingVertical: 6,
    borderRadius: 20, borderWidth: 1, borderColor: colors.border,
    marginRight: 8, backgroundColor: colors.surface,
  },
  filterChipActive: { backgroundColor: colors.brand, borderColor: colors.brand },
  filterChipText: { fontSize: 12, color: colors.textSecondary },
  filterChipTextActive: { color: '#FFF', fontWeight: '600' },

  submitBtn: {
    backgroundColor: colors.brand,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: spacing.md,
    minHeight: 44,    // WCAG 2.5.8
  },
  submitBtnDisabled: { opacity: 0.5 },
  submitText: { fontFamily: typography.fontBodySemiBold, color: colors.textOnBrand, fontSize: typography.sizeBody, letterSpacing: 0.3 },

  suggestSection: { marginBottom: 16 },
  suggestTitle:   { fontSize: 13, fontWeight: '700', color: colors.textSecondary, marginBottom: 8 },
  suggestItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: colors.surface,
    borderRadius: 10,
    padding: 12,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: colors.border,
  },
  suggestArrow: { fontSize: 16, color: colors.brand, marginRight: 8, marginTop: -1 },
  suggestText:  { flex: 1, fontSize: 13, color: colors.textPrimary, lineHeight: 18 },

  errorBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#FCA5A5',
    marginBottom: 16,
  },
  errorTitle: { fontSize: 14, fontWeight: '700', color: colors.error, marginBottom: 6 },
  errorText:  { fontSize: 13, color: '#7F1D1D', lineHeight: 20, fontFamily: 'monospace' },

  answerCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    overflow: 'hidden',
    elevation: 4,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 1,
  },
  answerHeader: {
    backgroundColor: colors.brandNavy,
    paddingHorizontal: spacing.base,
    paddingVertical: spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  answerHeaderText: { fontFamily: typography.fontBodyBold, color: colors.textOnNavy, fontSize: typography.sizeSmall },
  modelBadge: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  modelText: { color: '#FFF', fontSize: 10, fontWeight: '600' },
  markdownContainer: { padding: 16 },

  sourcesSection: {
    borderTopWidth: 1,
    borderTopColor: colors.border,
    padding: 16,
    backgroundColor: colors.surfaceAlt,
  },
  sourcesTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.textSecondary,
    marginBottom: 10,
  },
  citation: {
    backgroundColor: colors.surface,
    borderRadius: 10,
    padding: 10,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  citationHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 },
  citationNum: {
    width: 20, height: 20, borderRadius: 10,
    alignItems: 'center', justifyContent: 'center',
  },
  citationNumText: { color: '#FFF', fontSize: 10, fontWeight: '700' },
  citationSim: { fontSize: 10, color: colors.textMuted, marginLeft: 'auto' },
  citationTitle: { fontSize: 12, fontWeight: '600', color: colors.textPrimary, lineHeight: 16, marginBottom: 2 },
  citationEcli:  { fontSize: 10, color: colors.textMuted, fontFamily: 'monospace', marginBottom: 2 },
  citationDate:  { fontSize: 10, color: colors.textMuted },
  citationUrl:   { fontSize: 10, color: colors.brand, textDecorationLine: 'underline', marginTop: 4 },

  answerDisclaimer: {
    padding: spacing.md,
    borderBottomLeftRadius: radius.lg,
    borderBottomRightRadius: radius.lg,
  },
});

const markdownStyles = {
  body: { fontSize: 14, color: colors.textPrimary, lineHeight: 22 },
  heading1: { fontSize: 18, fontWeight: '700', color: colors.textPrimary, marginBottom: 8 },
  heading2: { fontSize: 16, fontWeight: '700', color: colors.brandNavy, marginBottom: 6 },
  heading3: { fontSize: 14, fontWeight: '700', color: colors.textSecondary, marginBottom: 4 },
  strong:   { fontWeight: '700', color: colors.textPrimary },
  em:       { fontStyle: 'italic', color: colors.textSecondary },
  bullet_list: { marginLeft: 8 },
  list_item: { marginBottom: 4 },
  code_inline: {
    backgroundColor: colors.surfaceAlt,
    paddingHorizontal: 4,
    borderRadius: 4,
    fontFamily: 'monospace',
    fontSize: 12,
  },
  blockquote: {
    borderWidth: 1,
    borderColor: colors.border,
    paddingLeft: 10,
    backgroundColor: colors.surfaceAlt,
    borderRadius: 4,
    marginVertical: 6,
    padding: 8,
  },
  hr: { borderBottomColor: colors.border, borderBottomWidth: 1, marginVertical: 12 },
};
