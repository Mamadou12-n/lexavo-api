import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { translations } from '../i18n/translations';

export const LANG_KEY = '@lexavo_lang';
const LEGACY_LANG_KEYS = ['lexavo_lang', '@lexavo_language'];

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
        if (v && mounted) setLangState(v);
      } catch (_) {}
    })();
    return () => { mounted = false; };
  }, []);

  const setLang = async (code) => {
    setLangState(code);
    await AsyncStorage.setItem(LANG_KEY, code).catch(() => {});
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
