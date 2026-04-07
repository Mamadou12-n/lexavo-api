/**
 * notifications.js — Lexavo push notification utilities
 * Utilise expo-notifications + expo-device
 */

import * as Notifications from 'expo-notifications';
import * as Device        from 'expo-device';
import { Platform }       from 'react-native';
import AsyncStorage       from '@react-native-async-storage/async-storage';

export const PUSH_TOKEN_KEY  = '@lexavo_push_token';
export const NOTIF_PREFS_KEY = '@lexavo_notif_prefs';

export const DEFAULT_PREFS = {
  legal_alerts:   true,   // nouvelles lois & jurisprudence
  deadlines:      true,   // rappels de délais juridiques
  news:           false,  // actus juridiques belges
  subscription:   true,   // rappels & renouvellement
};

// Comportement de l'app quand une notif arrive en foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge:  true,
  }),
});

/**
 * Demande les permissions et retourne le push token Expo.
 * Retourne null si refusé ou sur simulateur.
 */
export async function registerForPushNotifications() {
  if (!Device.isDevice) {
    console.warn('[Notifications] Simulateur — push non disponible.');
    return null;
  }

  const { status: existing } = await Notifications.getPermissionsAsync();
  let finalStatus = existing;

  if (existing !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    return null;
  }

  // Android — créer les canaux
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('legal-alerts', {
      name:             '⚖️ Alertes législatives',
      importance:       Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor:       '#D4A017',
      description:      'Nouvelles lois, arrêts et jurisprudence belge',
    });

    await Notifications.setNotificationChannelAsync('deadlines', {
      name:             '⏱ Rappels de délais',
      importance:       Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 500, 250, 500],
      lightColor:       '#E74C3C',
      description:      'Délais légaux et prescriptions',
    });

    await Notifications.setNotificationChannelAsync('news', {
      name:             '📰 Actus juridiques',
      importance:       Notifications.AndroidImportance.DEFAULT,
      lightColor:       '#2980B9',
      description:      'Actualités du droit belge',
    });

    await Notifications.setNotificationChannelAsync('subscription', {
      name:             '⭐ Abonnement',
      importance:       Notifications.AndroidImportance.LOW,
      lightColor:       '#C45A2D',
      description:      'Informations d\'abonnement Lexavo',
    });
  }

  try {
    const tokenResponse = await Notifications.getExpoPushTokenAsync({
      projectId: process.env.EXPO_PUBLIC_PROJECT_ID ?? 'lexavo-app',
    });
    const token = tokenResponse.data;
    await AsyncStorage.setItem(PUSH_TOKEN_KEY, token);
    return token;
  } catch (e) {
    console.warn('[Notifications] Token error:', e.message);
    return null;
  }
}

/**
 * Planifie une notification locale (rappel de délai).
 */
export async function scheduleDeadlineReminder({ title, body, date, data = {} }) {
  return await Notifications.scheduleNotificationAsync({
    content: {
      title,
      body,
      data,
      sound:    true,
      priority: Notifications.AndroidNotificationPriority.HIGH,
      channelId: 'deadlines',
    },
    trigger: { date: new Date(date) },
  });
}

/**
 * Annule une notification planifiée.
 */
export async function cancelNotification(id) {
  await Notifications.cancelScheduledNotificationAsync(id);
}

/**
 * Retourne toutes les notifications planifiées.
 */
export async function getScheduledNotifications() {
  return await Notifications.getAllScheduledNotificationsAsync();
}

/**
 * Annule toutes les notifications planifiées.
 */
export async function cancelAllNotifications() {
  await Notifications.cancelAllScheduledNotificationsAsync();
}

/**
 * Remet à zéro le badge de l'icône (iOS).
 */
export async function clearBadge() {
  await Notifications.setBadgeCountAsync(0);
}

/**
 * Envoie une notification test locale immédiate.
 */
export async function sendTestNotification() {
  await Notifications.scheduleNotificationAsync({
    content: {
      title: '⚖️ Lexavo — Test notification',
      body:  'Vos alertes juridiques belges fonctionnent correctement.',
      data:  { type: 'test' },
      channelId: 'legal-alerts',
    },
    trigger: { seconds: 2 },
  });
}

/**
 * Charge les préférences de notification depuis AsyncStorage.
 */
export async function loadNotifPrefs() {
  try {
    const raw = await AsyncStorage.getItem(NOTIF_PREFS_KEY);
    if (raw) return { ...DEFAULT_PREFS, ...JSON.parse(raw) };
  } catch (_) {}
  return { ...DEFAULT_PREFS };
}

/**
 * Sauvegarde les préférences de notification.
 */
export async function saveNotifPrefs(prefs) {
  await AsyncStorage.setItem(NOTIF_PREFS_KEY, JSON.stringify(prefs));
}
