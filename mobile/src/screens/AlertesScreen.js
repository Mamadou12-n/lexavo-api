import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, RefreshControl,
} from 'react-native';
import { getAlertDomains, getAlertFeed, saveAlertPreferences } from '../api/client';
import { colors } from '../theme/colors';
import { LinearGradient } from 'expo-linear-gradient';

const ALERT_DARK = '#D4A017';

export default function AlertesScreen() {
  const [domains, setDomains]       = useState([]);
  const [selected, setSelected]     = useState([]);
  const [feed, setFeed]             = useState([]);
  const [fetchingDomains, setFetchingDomains] = useState(true);
  const [loadingFeed, setLoadingFeed] = useState(false);
  const [saving, setSaving]         = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError]           = useState(null);

  useEffect(() => {
    getAlertDomains()
      .then((d) => {
        setDomains(d.domains ?? []);
        const all = (d.domains ?? []).map((x) => x.id);
        setSelected(all);
      })
      .catch(() => {})
      .finally(() => setFetchingDomains(false));
  }, []);

  const loadFeed = async (refresh = false) => {
    if (refresh) setRefreshing(true);
    else setLoadingFeed(true);
    setError(null);
    try {
      const data = await getAlertFeed(selected);
      setFeed(data.alerts ?? []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur réseau');
    } finally {
      setLoadingFeed(false);
      setRefreshing(false);
    }
  };

  const toggleDomain = (id) => {
    setSelected((s) =>
      s.includes(id) ? s.filter((x) => x !== id) : [...s, id]
    );
  };

  const save = async () => {
    setSaving(true);
    try {
      await saveAlertPreferences(selected);
      await loadFeed();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (fetchingDomains) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={ALERT_DARK} size="large" />
      </View>
    );
  }

  const URGENCY_DOT = { critical: '#E74C3C', high: '#E67E22', medium: '#F39C12', low: '#27AE60' };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => loadFeed(true)} tintColor={ALERT_DARK} />
      }
    >
      {/* Domain selector */}
      <LinearGradient colors={['#5C3D00', '#D4A017']} style={styles.heroHeader}>
        <Text style={styles.heroEmoji}>🔔</Text>
        <Text style={styles.heroTitle}>Alertes — Veille législative</Text>
        <Text style={styles.heroSub}>Choisissez vos domaines juridiques</Text>
      </LinearGradient>

      <View style={styles.card}>
        <View style={styles.domainsGrid}>
          {domains.map((d) => (
            <TouchableOpacity activeOpacity={0.75}
              key={d.id}
              style={[styles.domainChip, selected.includes(d.id) && styles.domainChipActive]}
              onPress={() => toggleDomain(d.id)}
            >
              <Text style={styles.domainEmoji}>{d.emoji ?? '📋'}</Text>
              <Text style={[styles.domainLabel, selected.includes(d.id) && styles.domainLabelActive]}>
                {d.label}
              </Text>
              {selected.includes(d.id) && <Text style={styles.domainCheck}>✓</Text>}
            </TouchableOpacity>
          ))}
        </View>
        <TouchableOpacity activeOpacity={0.75}
          style={[styles.btn, saving && styles.btnDisabled]}
          onPress={save}
          disabled={saving}
        >
          {saving
            ? <ActivityIndicator color="#FFF" />
            : <Text style={styles.btnText}>🔔  Voir mes alertes ({selected.length} domaines)</Text>
          }
        </TouchableOpacity>
      </View>

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>⚠️ {error}</Text>
        </View>
      )}

      {loadingFeed && (
        <View style={styles.center}>
          <ActivityIndicator color={ALERT_DARK} />
          <Text style={styles.loadingText}>Chargement des alertes...</Text>
        </View>
      )}

      {/* Feed */}
      {feed.length > 0 && (
        <View>
          <Text style={styles.feedTitle}>📰 {feed.length} alerte{feed.length > 1 ? 's' : ''}</Text>
          {feed.map((alert, i) => (
            <View key={alert.id ?? i} style={styles.alertCard}>
              <View style={styles.alertHeader}>
                <View style={[styles.urgencyDot, { backgroundColor: URGENCY_DOT[alert.urgency] ?? '#ccc' }]} />
                <View style={styles.domainBadge}>
                  <Text style={styles.domainBadgeText}>{alert.domain}</Text>
                </View>
                <Text style={styles.alertDate}>{alert.date?.slice(0, 10) ?? ''}</Text>
              </View>
              <Text style={styles.alertTitle}>{alert.title}</Text>
              {alert.summary && (
                <Text style={styles.alertSummary} numberOfLines={3}>{alert.summary}</Text>
              )}
              <Text style={styles.alertSource}>📌 {alert.source}</Text>
            </View>
          ))}
        </View>
      )}

      {feed.length > 0 && (
        <View style={{ marginHorizontal: 16, marginBottom: 12, padding: 10, backgroundColor: '#FFFBEB', borderRadius: 8, borderWidth: 1, borderColor: '#FDE68A' }}>
          <Text style={{ fontSize: 10, color: '#92400E', textAlign: 'center', fontStyle: 'italic', lineHeight: 14 }}>
            ⚖️ Lexavo est un outil d'information juridique. Il ne remplace pas un avocat ni un conseiller juridique professionnel.
          </Text>
        </View>
      )}

      {feed.length === 0 && !loadingFeed && !error && (
        <View style={styles.emptyBox}>
          <Text style={styles.emptyEmoji}>🔔</Text>
          <Text style={styles.emptyText}>Sélectionnez vos domaines et appuyez sur "Voir mes alertes"</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content:   { padding: 16, paddingBottom: 40 },
  center:    { alignItems: 'center', justifyContent: 'center', padding: 24 },
  loadingText: { marginTop: 8, color: colors.textMuted, fontSize: 12 },

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

  domainsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 14 },
  domainChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 10,
    paddingVertical: 7,
    backgroundColor: colors.background,
  },
  domainChipActive: { borderColor: ALERT_DARK, backgroundColor: '#EDF2F7' },
  domainEmoji: { fontSize: 14 },
  domainLabel: { fontSize: 12, color: colors.textSecondary },
  domainLabelActive: { color: ALERT_DARK, fontWeight: '700' },
  domainCheck: { fontSize: 11, color: ALERT_DARK, fontWeight: '700' },

  btn: {
    backgroundColor: ALERT_DARK,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  btnDisabled: { opacity: 0.45 },
  btnText: { color: '#FFF', fontSize: 14, fontWeight: '700' },

  errorBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#FCA5A5',
    marginBottom: 12,
  },
  errorText: { fontSize: 13, color: colors.error, fontWeight: '600' },

  feedTitle: { fontSize: 14, fontWeight: '700', color: colors.textSecondary, marginBottom: 10 },

  alertCard: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    elevation: 2,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 1,
  },
  alertHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  urgencyDot: { width: 8, height: 8, borderRadius: 4 },
  domainBadge: {
    backgroundColor: '#EDF2F7',
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  domainBadgeText: { fontSize: 10, color: ALERT_DARK, fontWeight: '600', textTransform: 'capitalize' },
  alertDate: { fontSize: 10, color: colors.textMuted, marginLeft: 'auto' },

  alertTitle:   { fontSize: 13, fontWeight: '700', color: colors.textPrimary, marginBottom: 4, lineHeight: 18 },
  alertSummary: { fontSize: 12, color: colors.textSecondary, lineHeight: 17, marginBottom: 6 },
  alertSource:  { fontSize: 11, color: colors.textMuted },

  emptyBox: { alignItems: 'center', padding: 32 },
  emptyEmoji: { fontSize: 36, marginBottom: 10 },
  emptyText: { fontSize: 13, color: colors.textMuted, textAlign: 'center', lineHeight: 19 },
});
