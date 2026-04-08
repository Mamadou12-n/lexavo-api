import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { translations } from '../i18n/translations';

export const LANG_KEY = 'lexavo_lang';

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState('fr');

  useEffect(() => {
    AsyncStorage.getItem(LANG_KEY).then(v => { if (v) setLangState(v); }).catch(() => {});
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
