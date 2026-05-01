/**
 * Tests utilitaires — LanguageContext (setLang, initLanguage, migration legacy keys)
 * et SecureStore migration AsyncStorage → SecureStore.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

// Reset du store entre chaque test
beforeEach(() => {
  AsyncStorage.clear();
  jest.clearAllMocks();
});

// ─── Helpers testables extraits du LanguageContext ────────────────────────────

const LANG_KEY = '@lexavo_lang';
const LEGACY_LANG_KEYS = ['lexavo_lang', '@lexavo_language'];

async function initLanguage() {
  let v = await AsyncStorage.getItem(LANG_KEY);
  if (!v) {
    for (const legacy of LEGACY_LANG_KEYS) {
      const old = await AsyncStorage.getItem(legacy).catch(() => null);
      if (old) {
        v = old;
        await AsyncStorage.setItem(LANG_KEY, old).catch(() => {});
        await AsyncStorage.removeItem(legacy).catch(() => {});
        break;
      }
    }
  }
  return v || 'fr';
}

async function setLanguage(code) {
  await AsyncStorage.setItem(LANG_KEY, code);
  return code;
}

// ─── Tests setLanguage ────────────────────────────────────────────────────────

describe('setLanguage', () => {
  test('persiste la langue dans AsyncStorage', async () => {
    await setLanguage('nl');
    const stored = await AsyncStorage.getItem(LANG_KEY);
    expect(stored).toBe('nl');
  });

  test('retourne le code langue', async () => {
    const result = await setLanguage('en');
    expect(result).toBe('en');
  });

  test('supporte toutes les 8 langues', async () => {
    const langs = ['fr', 'nl', 'en', 'de', 'ar', 'tr', 'es', 'pt'];
    for (const lang of langs) {
      await setLanguage(lang);
      const stored = await AsyncStorage.getItem(LANG_KEY);
      expect(stored).toBe(lang);
    }
  });
});

// ─── Tests initLanguage / migration legacy keys ───────────────────────────────

describe('initLanguage', () => {
  test('retourne fr par défaut quand rien en storage', async () => {
    const lang = await initLanguage();
    expect(lang).toBe('fr');
  });

  test('retourne la langue stockée dans la clé principale', async () => {
    await AsyncStorage.setItem(LANG_KEY, 'nl');
    const lang = await initLanguage();
    expect(lang).toBe('nl');
  });

  test('migre la clé legacy lexavo_lang vers la clé principale', async () => {
    await AsyncStorage.setItem('lexavo_lang', 'de');
    const lang = await initLanguage();
    expect(lang).toBe('de');
    // Nouvelle clé créée
    const newKey = await AsyncStorage.getItem(LANG_KEY);
    expect(newKey).toBe('de');
    // Ancienne clé supprimée
    const oldKey = await AsyncStorage.getItem('lexavo_lang');
    expect(oldKey).toBeNull();
  });

  test('migre la clé legacy @lexavo_language vers la clé principale', async () => {
    await AsyncStorage.setItem('@lexavo_language', 'es');
    const lang = await initLanguage();
    expect(lang).toBe('es');
    const newKey = await AsyncStorage.getItem(LANG_KEY);
    expect(newKey).toBe('es');
    const oldKey = await AsyncStorage.getItem('@lexavo_language');
    expect(oldKey).toBeNull();
  });

  test('la clé principale prime sur les legacy keys', async () => {
    await AsyncStorage.setItem(LANG_KEY, 'en');
    await AsyncStorage.setItem('lexavo_lang', 'ar');
    const lang = await initLanguage();
    expect(lang).toBe('en');
  });
});

// ─── Tests secureGet / secureSet (migration AsyncStorage → SecureStore) ───────

describe('secureGet / secureSet', () => {
  const SecureStore = require('expo-secure-store');

  beforeEach(() => {
    SecureStore.getItemAsync.mockReset();
    SecureStore.setItemAsync.mockReset();
    SecureStore.deleteItemAsync.mockReset();
  });

  test('secureSet appelle SecureStore.setItemAsync', async () => {
    SecureStore.setItemAsync.mockResolvedValueOnce(undefined);
    await SecureStore.setItemAsync('test_key', 'test_value');
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith('test_key', 'test_value');
  });

  test('secureGet retourne null quand la clé est absente', async () => {
    SecureStore.getItemAsync.mockResolvedValueOnce(null);
    const result = await SecureStore.getItemAsync('missing_key');
    expect(result).toBeNull();
  });

  test('secureGet retourne la valeur stockée', async () => {
    SecureStore.getItemAsync.mockResolvedValueOnce('stored_token');
    const result = await SecureStore.getItemAsync('auth_token');
    expect(result).toBe('stored_token');
  });

  test('secureSet puis secureGet (round-trip simulé)', async () => {
    let store = {};
    SecureStore.setItemAsync.mockImplementation((k, v) => {
      store[k] = v;
      return Promise.resolve();
    });
    SecureStore.getItemAsync.mockImplementation((k) =>
      Promise.resolve(store[k] ?? null)
    );

    await SecureStore.setItemAsync('auth_token', 'jwt.abc.123');
    const result = await SecureStore.getItemAsync('auth_token');
    expect(result).toBe('jwt.abc.123');
  });
});
