/**
 * Tests — notifications.js utils
 * Teste les fonctions pures et la gestion des préférences.
 */

import {
  DEFAULT_PREFS,
  loadNotifPrefs,
  saveNotifPrefs,
  PUSH_TOKEN_KEY,
  NOTIF_PREFS_KEY,
} from '../../utils/notifications';

// AsyncStorage est mocké automatiquement via moduleNameMapper
import AsyncStorage from '@react-native-async-storage/async-storage';

beforeEach(() => {
  AsyncStorage.clear();
  jest.clearAllMocks();
});

// ── DEFAULT_PREFS ────────────────────────────────────────────────────────────

describe('DEFAULT_PREFS', () => {
  it('contient les 4 types de notifications', () => {
    expect(DEFAULT_PREFS).toHaveProperty('legal_alerts');
    expect(DEFAULT_PREFS).toHaveProperty('deadlines');
    expect(DEFAULT_PREFS).toHaveProperty('news');
    expect(DEFAULT_PREFS).toHaveProperty('subscription');
  });

  it('active legal_alerts par défaut', () => {
    expect(DEFAULT_PREFS.legal_alerts).toBe(true);
  });

  it('active deadlines par défaut', () => {
    expect(DEFAULT_PREFS.deadlines).toBe(true);
  });

  it('désactive news par défaut (non-intrusif)', () => {
    expect(DEFAULT_PREFS.news).toBe(false);
  });

  it('active subscription par défaut', () => {
    expect(DEFAULT_PREFS.subscription).toBe(true);
  });
});

// ── Clés AsyncStorage ────────────────────────────────────────────────────────

describe('clés AsyncStorage', () => {
  it('PUSH_TOKEN_KEY est une string non vide', () => {
    expect(typeof PUSH_TOKEN_KEY).toBe('string');
    expect(PUSH_TOKEN_KEY.length).toBeGreaterThan(0);
  });

  it('NOTIF_PREFS_KEY est une string non vide', () => {
    expect(typeof NOTIF_PREFS_KEY).toBe('string');
    expect(NOTIF_PREFS_KEY.length).toBeGreaterThan(0);
  });

  it('PUSH_TOKEN_KEY et NOTIF_PREFS_KEY sont différents', () => {
    expect(PUSH_TOKEN_KEY).not.toBe(NOTIF_PREFS_KEY);
  });
});

// ── loadNotifPrefs ───────────────────────────────────────────────────────────

describe('loadNotifPrefs', () => {
  it('retourne DEFAULT_PREFS quand rien n\'est stocké', async () => {
    const prefs = await loadNotifPrefs();
    expect(prefs).toEqual(DEFAULT_PREFS);
  });

  it('retourne les prefs stockées', async () => {
    await saveNotifPrefs({ legal_alerts: false, deadlines: true, news: true, subscription: false });
    const prefs = await loadNotifPrefs();
    expect(prefs.legal_alerts).toBe(false);
    expect(prefs.news).toBe(true);
    expect(prefs.subscription).toBe(false);
  });

  it('merge avec DEFAULT_PREFS (propriétés manquantes = valeurs par défaut)', async () => {
    await AsyncStorage.setItem(NOTIF_PREFS_KEY, JSON.stringify({ legal_alerts: false }));
    const prefs = await loadNotifPrefs();
    expect(prefs.legal_alerts).toBe(false);
    // Propriétés manquantes → valeurs par défaut
    expect(prefs.deadlines).toBe(DEFAULT_PREFS.deadlines);
    expect(prefs.news).toBe(DEFAULT_PREFS.news);
    expect(prefs.subscription).toBe(DEFAULT_PREFS.subscription);
  });

  it('retourne DEFAULT_PREFS si JSON invalide en storage', async () => {
    await AsyncStorage.setItem(NOTIF_PREFS_KEY, 'INVALID_JSON{{{');
    const prefs = await loadNotifPrefs();
    expect(prefs).toEqual(DEFAULT_PREFS);
  });
});

// ── saveNotifPrefs ───────────────────────────────────────────────────────────

describe('saveNotifPrefs', () => {
  it('sauvegarde les préférences dans AsyncStorage', async () => {
    const newPrefs = { legal_alerts: false, deadlines: false, news: true, subscription: true };
    await saveNotifPrefs(newPrefs);
    const stored = JSON.parse(await AsyncStorage.getItem(NOTIF_PREFS_KEY));
    expect(stored).toEqual(newPrefs);
  });

  it('écrase les préférences précédentes', async () => {
    await saveNotifPrefs({ legal_alerts: true });
    await saveNotifPrefs({ legal_alerts: false, news: true });
    const stored = JSON.parse(await AsyncStorage.getItem(NOTIF_PREFS_KEY));
    expect(stored.legal_alerts).toBe(false);
    expect(stored.news).toBe(true);
  });

  it('saveNotifPrefs + loadNotifPrefs = round-trip fidèle', async () => {
    const prefs = { legal_alerts: false, deadlines: true, news: false, subscription: false };
    await saveNotifPrefs(prefs);
    const loaded = await loadNotifPrefs();
    // Les propriétés sauvegardées correspondent
    expect(loaded.legal_alerts).toBe(false);
    expect(loaded.deadlines).toBe(true);
    expect(loaded.news).toBe(false);
    expect(loaded.subscription).toBe(false);
  });
});
