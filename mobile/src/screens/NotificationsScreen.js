import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Switch, TouchableOpacity,
  ActivityIndicator, Platform, Alert,
} from 'react-native';
import * as Notifications from 'expo-notifications';
import AsyncStorage       from '@react-native-async-storage/async-storage';
import {
  registerForPushNotifications,
  sendTestNotification,
  getScheduledNotifications,
  cancelNotification,
  cancelAllNotifications,
  loadNotifPrefs,
  saveNotifPrefs,
  PUSH_TOKEN_KEY,
} from '../utils/notifications';
import { registerPushToken, updateNotificationPreferences } from '../api/client';
import { colors } from '../theme/colors';
import { LinearGradient } from 'expo-linear-gradient';

const NAVY   = '#1C2B3A';
const ORANGE = '#C45A2D';

const NOTIF_TYPES = [
  {
    key:     'legal_alerts',
    icon:    '⚖️',
    title:   'Alertes législatives',
    desc:    'Nouvelles lois, arrêts de la Cour de cassation et jurisprudence belge',
    channel: 'legal-alerts',
    color:   '#D4A017',
  },
  {
    key:     'deadlines',
    icon:    '⏱',
    title:   'Rappels de délais',
    desc:    'Délais légaux, prescriptions et échéances de votre dossier',
    channel: 'deadlines',
    color:   '#E74C3C',
  },
  {
    key:     'news',
    icon:    '📰',
    title:   'Actus juridiques',
    desc:    'Actualités hebdomadaires du droit belge (FR/NL)',
    channel: 'news',
    color:   '#2980B9',
  },
  {
    key:     'subscription',
    icon:    '⭐',
    title:   'Abonnement',
    desc:    'Rappels de renouvellement et informations de facturation',
    channel: 'subscription',
    color:   ORANGE,
  },
];

export default function NotificationsScreen() {
  const [permStatus, setPermStatus]     = useState(null);
  const [pushToken, setPushToken]       = useState(null);
  const [prefs, setPrefs]               = useState(null);
  const [scheduled, setScheduled]       = useState([]);
  const [registering, setRegistering]   = useState(false);
  const [testing, setTesting]           = useState(false);
  const [loading, setLoading]           = useState(true);
  const notifListener  = useRef(null);
  const responseListener = useRef(null);

  useEffect(() => {
    init();
    notifListener.current = Notifications.addNotificationReceivedListener(() => {
      loadScheduled();
    });
    responseListener.current = Notifications.addNotificationResponseReceivedListener(() => {
      // Handle tap on notification
    });
    return () => {
      notifListener.current?.remove();
      responseListener.current?.remove();
    };
  }, []);

  const init = async () => {
    const [{ status }, storedToken, loadedPrefs, sched] = await Promise.all([
      Notifications.getPermissionsAsync(),
      AsyncStorage.getItem(PUSH_TOKEN_KEY),
      loadNotifPrefs(),
      getScheduledNotifications(),
    ]);
    setPermStatus(status);
    setPushToken(storedToken);
    setPrefs(loadedPrefs);
    setScheduled(sched);
    setLoading(false);
  };

  const loadScheduled = async () => {
    const sched = await getScheduledNotifications();
    setScheduled(sched);
  };

  const requestPermission = async () => {
    setRegistering(true);
    try {
      const token = await registerForPushNotifications();
      if (token) {
        setPushToken(token);
        setPermStatus('granted');
        try { await registerPushToken(token); } catch (_) {}
        Alert.alert('✅ Notifications activées', 'Vous recevrez désormais vos alertes juridiques.');
      } else {
        setPermStatus('denied');
        Alert.alert(
          'Permission refusée',
          'Activez les notifications dans les réglages de votre appareil.',
        );
      }
    } finally {
      setRegistering(false);
    }
  };

  const togglePref = async (key) => {
    const newPrefs = { ...prefs, [key]: !prefs[key] };
    setPrefs(newPrefs);
    await saveNotifPrefs(newPrefs);
    if (pushToken) {
      try { await updateNotificationPreferences(pushToken, newPrefs); } catch (_) {}
    }
  };

  const handleTest = async () => {
    if (permStatus !== 'granted') {
      Alert.alert('Permission requise', 'Activez d\'abord les notifications.');
      return;
    }
    setTesting(true);
    try {
      await sendTestNotification();
      Alert.alert('📲 Envoyé', 'Une notification test arrivera dans ~2 secondes.');
    } finally {
      setTesting(false);
    }
  };

  const handleCancelScheduled = async (id) => {
    await cancelNotification(id);
    await loadScheduled();
  };

  const handleCancelAll = () => {
    Alert.alert(
      'Annuler tous les rappels',
      'Tous vos rappels de délais planifiés seront supprimés.',
      [
        { text: 'Non', style: 'cancel' },
        {
          text: 'Oui, annuler tout',
          style: 'destructive',
          onPress: async () => {
            await cancelAllNotifications();
            setScheduled([]);
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={NAVY} size="large" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

      <LinearGradient colors={['#0A1628', '#1A3A5C']} style={styles.heroHeader}>
        <Text style={styles.heroEmoji}>🔔</Text>
        <Text style={styles.heroTitle}>Notifications</Text>
        <Text style={styles.heroSub}>Gérez vos alertes juridiques</Text>
      </LinearGradient>

      {/* Permission status */}
      <View style={[
        styles.permBox,
        permStatus === 'granted' ? styles.permGranted : styles.permDenied,
      ]}>
        <View style={styles.permRow}>
          <Text style={styles.permIcon}>
            {permStatus === 'granted' ? '🔔' : '🔕'}
          </Text>
          <View style={styles.permInfo}>
            <Text style={styles.permTitle}>
              {permStatus === 'granted' ? 'Notifications activées' : 'Notifications désactivées'}
            </Text>
            {pushToken && (
              <Text style={styles.permToken} numberOfLines={1}>
                Token : {pushToken.slice(0, 24)}…
              </Text>
            )}
          </View>
        </View>
        {permStatus !== 'granted' && (
          <TouchableOpacity activeOpacity={0.75}
            style={styles.enableBtn}
            onPress={requestPermission}
            disabled={registering}
          >
            {registering
              ? <ActivityIndicator color="#FFF" size="small" />
              : <Text style={styles.enableBtnText}>Activer les notifications</Text>
            }
          </TouchableOpacity>
        )}
      </View>

      {/* Preferences */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📋 Préférences de notification</Text>
        {prefs && NOTIF_TYPES.map((type, i) => (
          <View
            key={type.key}
            style={[
              styles.prefRow,
              i < NOTIF_TYPES.length - 1 && styles.prefRowBorder,
            ]}
          >
            <View style={[styles.prefIconBox, { backgroundColor: `${type.color}20` }]}>
              <Text style={styles.prefIcon}>{type.icon}</Text>
            </View>
            <View style={styles.prefInfo}>
              <Text style={styles.prefTitle}>{type.title}</Text>
              <Text style={styles.prefDesc}>{type.desc}</Text>
            </View>
            <Switch
              value={prefs[type.key]}
              onValueChange={() => togglePref(type.key)}
              trackColor={{ false: colors.border, true: type.color }}
              thumbColor="#FFF"
              disabled={permStatus !== 'granted'}
            />
          </View>
        ))}
      </View>

      {/* Scheduled reminders */}
      {scheduled.length > 0 && (
        <View style={styles.card}>
          <View style={styles.scheduledHeader}>
            <Text style={styles.cardTitle}>⏱ Rappels planifiés ({scheduled.length})</Text>
            <TouchableOpacity activeOpacity={0.75} onPress={handleCancelAll}>
              <Text style={styles.clearAllText}>Tout annuler</Text>
            </TouchableOpacity>
          </View>
          {scheduled.map((n, i) => {
            const trigger = n.trigger;
            const dateStr = trigger?.value
              ? new Date(trigger.value * 1000).toLocaleDateString('fr-BE')
              : trigger?.seconds
              ? `Dans ${trigger.seconds}s`
              : 'Planifié';
            return (
              <View key={n.identifier} style={styles.scheduledItem}>
                <View style={styles.scheduledInfo}>
                  <Text style={styles.scheduledTitle}>{n.content.title}</Text>
                  <Text style={styles.scheduledDate}>📅 {dateStr}</Text>
                </View>
                <TouchableOpacity activeOpacity={0.75}
                  style={styles.cancelNotifBtn}
                  onPress={() => handleCancelScheduled(n.identifier)}
                >
                  <Text style={styles.cancelNotifText}>✕</Text>
                </TouchableOpacity>
              </View>
            );
          })}
        </View>
      )}

      {/* Test */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🧪 Tester les notifications</Text>
        <Text style={styles.testDesc}>
          Envoie une notification test pour vérifier que tout fonctionne correctement.
        </Text>
        <TouchableOpacity activeOpacity={0.75}
          style={[styles.testBtn, permStatus !== 'granted' && styles.testBtnDisabled]}
          onPress={handleTest}
          disabled={testing || permStatus !== 'granted'}
        >
          {testing
            ? <ActivityIndicator color="#FFF" size="small" />
            : <Text style={styles.testBtnText}>📲 Envoyer une notification test</Text>
          }
        </TouchableOpacity>
      </View>

      {/* Info */}
      <View style={styles.infoBox}>
        <Text style={styles.infoText}>
          ℹ️ Les notifications push sont envoyées via le service Expo Push Notifications.
          Aucune donnée personnelle n'est transmise pour l'envoi de notifications.{'\n\n'}
          Pour désactiver définitivement les notifications, rendez-vous dans les
          réglages de votre appareil → Lexavo → Notifications.
        </Text>
      </View>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content:   { padding: 16, paddingBottom: 40 },
  center:    { flex: 1, alignItems: 'center', justifyContent: 'center' },

  heroHeader: { borderRadius: 16, padding: 20, marginBottom: 14, alignItems: 'center' },
  heroEmoji: { fontSize: 32, marginBottom: 8 },
  heroTitle: { fontSize: 20, fontWeight: '900', color: '#FFF', letterSpacing: 0.5 },
  heroSub: { fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4, textAlign: 'center' },

  permBox: {
    borderRadius: 14,
    padding: 14,
    marginBottom: 14,
    borderWidth: 1,
  },
  permGranted: { backgroundColor: '#F0FDF4', borderColor: '#BBF7D0' },
  permDenied:  { backgroundColor: '#FEF2F2', borderColor: '#FCA5A5' },
  permRow:     { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 8 },
  permIcon:    { fontSize: 24 },
  permInfo:    { flex: 1 },
  permTitle:   { fontSize: 14, fontWeight: '700', color: colors.textPrimary },
  permToken:   { fontSize: 9, color: colors.textMuted, fontFamily: 'monospace', marginTop: 2 },
  enableBtn: {
    backgroundColor: NAVY,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 4,
  },
  enableBtnText: { color: '#FFF', fontSize: 14, fontWeight: '700' },

  card: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 14,
    marginBottom: 12,
    elevation: 2,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 1,
  },
  cardTitle: { fontSize: 13, fontWeight: '800', color: NAVY, marginBottom: 12 },

  prefRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 10,
  },
  prefRowBorder: { borderBottomWidth: 1, borderBottomColor: colors.border },
  prefIconBox: { width: 36, height: 36, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  prefIcon:  { fontSize: 18 },
  prefInfo:  { flex: 1 },
  prefTitle: { fontSize: 13, fontWeight: '600', color: colors.textPrimary },
  prefDesc:  { fontSize: 11, color: colors.textMuted, lineHeight: 15, marginTop: 2 },

  scheduledHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  clearAllText: { fontSize: 11, color: colors.error, fontWeight: '600' },
  scheduledItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: 10,
    marginBottom: 6,
  },
  scheduledInfo:  { flex: 1 },
  scheduledTitle: { fontSize: 12, fontWeight: '600', color: colors.textPrimary },
  scheduledDate:  { fontSize: 10, color: colors.textMuted, marginTop: 2 },
  cancelNotifBtn: { padding: 6 },
  cancelNotifText: { fontSize: 14, color: colors.textMuted, fontWeight: '700' },

  testDesc: { fontSize: 12, color: colors.textSecondary, lineHeight: 17, marginBottom: 12 },
  testBtn: {
    backgroundColor: NAVY,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
  },
  testBtnDisabled: { opacity: 0.45 },
  testBtnText: { color: '#FFF', fontSize: 13, fontWeight: '700' },

  infoBox: {
    backgroundColor: '#EFF6FF',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#BFDBFE',
  },
  infoText: { fontSize: 11, color: '#1E40AF', lineHeight: 17 },
});
