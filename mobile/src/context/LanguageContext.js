import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { I18nManager } from 'react-native';
import { translations } from '../i18n/translations';

const RTL_LANGS = ['ar'];

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
        if (v && mounted) {
          setLangState(v);
          applyRTL(v);
        } else {
          applyRTL('fr');
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
    setLangState(code);
    applyRTL(code);
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
