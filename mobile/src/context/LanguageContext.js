import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { I18nManager } from 'react-native';
import { translations } from '../i18n/translations';

// Refocalisation 2026-05-05 : 4 langues (FR/NL officielles BE + EN international + DE).
// Suppression ES/IT/PT/AR/TR. Plus de RTL pour le moment.
export const SUPPORTED_LANGS = ['fr', 'nl', 'en', 'de'];
const RTL_LANGS = [];

export const LANG_KEY = '@lexavo_lang';
const LEGACY_LANG_KEYS = ['lexavo_lang', '@lexavo_language'];

function normalizeLang(code) {
  if (!code) return 'fr';
  const lower = String(code).toLowerCase().slice(0, 2);
  return SUPPORTED_LANGS.includes(lower) ? lower : 'fr';
}

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState('fr');

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
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
        const normalized = normalizeLang(v);
        // Si l'utilisateur avait stocke une langue desormais non supportee
        // (ex : 'ar' avant le passage a 4 langues), on persiste le fallback 'fr'.
        if (v && v !== normalized) {
          await AsyncStorage.setItem(LANG_KEY, normalized).catch(() => {});
        }
        if (mounted) {
          setLangState(normalized);
          applyRTL(normalized);
        }
      } catch (_) {}
    })();
    return () => { mounted = false; };
  }, []);

  const applyRTL = (code) => {
    try {
      const shouldRTL = RTL_LANGS.includes(code);
      if (I18nManager.isRTL !== shouldRTL) {
        I18nManager.allowRTL(shouldRTL);
        I18nManager.forceRTL(shouldRTL);
        // Pour appliquer pleinement, l'app doit être relancée. C'est OK : RN
        // applique la valeur dès le redémarrage suivant. Pas de Updates.reloadAsync
        // ici pour éviter une dépendance expo-updates non garantie.
      }
    } catch (_) {}
  };

  const setLang = async (code) => {
    const normalized = normalizeLang(code);
    setLangState(normalized);
    applyRTL(normalized);
    await AsyncStorage.setItem(LANG_KEY, normalized).catch(() => {});
  };

  const t = (key) => {
    const data = translations[lang] || translations.fr;
    return data[key] ?? translations.fr[key] ?? key;
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used inside LanguageProvider');
  return ctx;
}
