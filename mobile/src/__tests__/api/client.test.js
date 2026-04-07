/**
 * Tests — client.js
 * Teste la gestion de l'URL API et les fonctions pures.
 */

import {
  getApiUrl,
  setApiUrl,
  initApiUrl,
  SOURCES,
} from '../../api/client';

import AsyncStorage from '@react-native-async-storage/async-storage';

beforeEach(() => {
  AsyncStorage.clear();
  jest.clearAllMocks();
});

// ── URL Management ───────────────────────────────────────────────────────────

describe('URL API management', () => {
  it('getApiUrl retourne l\'URL par défaut au démarrage', () => {
    const url = getApiUrl();
    expect(typeof url).toBe('string');
    expect(url.length).toBeGreaterThan(0);
    expect(url).toContain('localhost');
  });

  it('setApiUrl met à jour l\'URL courante', async () => {
    await setApiUrl('http://192.168.1.42:8000');
    expect(getApiUrl()).toBe('http://192.168.1.42:8000');
  });

  it('setApiUrl supprime le slash final', async () => {
    await setApiUrl('http://192.168.1.42:8000/');
    expect(getApiUrl()).toBe('http://192.168.1.42:8000');
  });

  it('setApiUrl persiste dans AsyncStorage', async () => {
    await setApiUrl('http://10.0.2.2:8000');
    const stored = await AsyncStorage.getItem('@jurisbe_api_url');
    expect(stored).toBe('http://10.0.2.2:8000');
  });

  it('initApiUrl restaure l\'URL depuis AsyncStorage', async () => {
    await AsyncStorage.setItem('@jurisbe_api_url', 'http://prod.lexavo.be:8000');
    await initApiUrl();
    expect(getApiUrl()).toBe('http://prod.lexavo.be:8000');
  });

  it('initApiUrl ne crash pas si rien n\'est stocké', async () => {
    await expect(initApiUrl()).resolves.not.toThrow();
  });
});

// ── SOURCES ──────────────────────────────────────────────────────────────────

describe('SOURCES', () => {
  it('est un tableau non vide', () => {
    expect(Array.isArray(SOURCES)).toBe(true);
    expect(SOURCES.length).toBeGreaterThan(0);
  });

  it('chaque source a les propriétés requises', () => {
    SOURCES.forEach((source) => {
      expect(source).toHaveProperty('label');
      expect(source).toHaveProperty('emoji');
      // key peut être null (option "Toutes les sources")
      expect(source).toHaveProperty('key');
    });
  });

  it('contient "HUDOC" (CEDH)', () => {
    const hudoc = SOURCES.find((s) => s.key === 'HUDOC');
    expect(hudoc).toBeDefined();
    expect(hudoc.emoji).toBe('🇪🇺');
  });

  it('contient "Juridat" (Cour de cassation belge)', () => {
    const juridat = SOURCES.find((s) => s.key === 'Juridat');
    expect(juridat).toBeDefined();
  });

  it('contient "APD" (RGPD belge)', () => {
    const apd = SOURCES.find((s) => s.key === 'APD');
    expect(apd).toBeDefined();
  });

  it('la première entrée est "Toutes les sources" (key=null)', () => {
    expect(SOURCES[0].key).toBeNull();
    expect(SOURCES[0].label).toContain('Toutes');
  });

  it('contient au moins 15 sources réelles', () => {
    const realSources = SOURCES.filter((s) => s.key !== null);
    expect(realSources.length).toBeGreaterThanOrEqual(15);
  });
});
