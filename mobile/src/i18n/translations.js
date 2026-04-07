/**
 * i18n — Lexavo
 * Translations FR / NL / EN using a simple object-based approach.
 * No extra dependency needed.
 */

import { Platform, NativeModules } from 'react-native';

export const translations = {
  fr: {
    app_name: 'Lexavo',
    welcome: 'Bienvenue',
    onboarding_title: 'Bienvenue sur Lexavo',
    onboarding_subtitle: 'Votre assistant juridique belge intelligent',
    ask_question: 'Poser une question',
    search: 'Rechercher',
    settings: 'Parametres',
    lawyers: 'Avocats',
    history: 'Historique',
    login: 'Connexion',
    register: 'Inscription',
    source_filter: 'Filtrer par source',
    disclaimer: 'Les informations fournies par Lexavo sont a titre informatif uniquement et ne constituent pas un conseil juridique professionnel.',
    cgu: 'Conditions generales d\'utilisation',
    privacy: 'Politique de confidentialite',
    no_results: 'Aucun resultat trouve',
    loading: 'Chargement...',
    error: 'Une erreur est survenue',
    send: 'Envoyer',
    language: 'Langue',
    dark_mode: 'Mode sombre',
    api_url: 'URL de l\'API',
    about: 'A propos',
  },
  nl: {
    app_name: 'Lexavo',
    welcome: 'Welkom',
    onboarding_title: 'Welkom bij Lexavo',
    onboarding_subtitle: 'Uw slimme Belgische juridische assistent',
    ask_question: 'Stel een vraag',
    search: 'Zoeken',
    settings: 'Instellingen',
    lawyers: 'Advocaten',
    history: 'Geschiedenis',
    login: 'Inloggen',
    register: 'Registreren',
    source_filter: 'Filter op bron',
    disclaimer: 'De informatie van Lexavo is uitsluitend bedoeld ter informatie en vormt geen professioneel juridisch advies.',
    cgu: 'Algemene voorwaarden',
    privacy: 'Privacybeleid',
    no_results: 'Geen resultaten gevonden',
    loading: 'Laden...',
    error: 'Er is een fout opgetreden',
    send: 'Verzenden',
    language: 'Taal',
    dark_mode: 'Donkere modus',
    api_url: 'API URL',
    about: 'Over',
  },
  en: {
    app_name: 'Lexavo',
    welcome: 'Welcome',
    onboarding_title: 'Welcome to Lexavo',
    onboarding_subtitle: 'Your smart Belgian legal assistant',
    ask_question: 'Ask a question',
    search: 'Search',
    settings: 'Settings',
    lawyers: 'Lawyers',
    history: 'History',
    login: 'Login',
    register: 'Register',
    source_filter: 'Filter by source',
    disclaimer: 'The information provided by Lexavo is for informational purposes only and does not constitute professional legal advice.',
    cgu: 'Terms of service',
    privacy: 'Privacy policy',
    no_results: 'No results found',
    loading: 'Loading...',
    error: 'An error occurred',
    send: 'Send',
    language: 'Language',
    dark_mode: 'Dark mode',
    api_url: 'API URL',
    about: 'About',
  },
};

/**
 * Returns the translated string for a given key and language.
 * Falls back to French if the key is not found in the requested language.
 *
 * @param {string} key   Translation key
 * @param {string} lang  Language code ('fr', 'nl', 'en')
 * @returns {string}
 */
export function t(key, lang = 'fr') {
  const langData = translations[lang] || translations.fr;
  return langData[key] ?? translations.fr[key] ?? key;
}

/**
 * Detects the device language and returns 'fr', 'nl', or 'en'.
 * Defaults to 'fr' if the device language is not supported.
 *
 * @returns {string}
 */
export function getDeviceLanguage() {
  let locale = '';

  try {
    if (Platform.OS === 'ios') {
      // iOS: AppleLocale or first item from AppleLanguages
      const settings =
        NativeModules.SettingsManager?.settings ||
        NativeModules.SettingsManager?.getConstants?.() ||
        {};
      locale =
        settings.AppleLocale ||
        (settings.AppleLanguages && settings.AppleLanguages[0]) ||
        '';
    } else {
      // Android: device locale from I18nManager or NativeModules
      locale =
        NativeModules.I18nManager?.localeIdentifier ||
        NativeModules.I18nManager?.getConstants?.()?.localeIdentifier ||
        '';
    }
  } catch (_) {
    locale = '';
  }

  const langCode = locale.toLowerCase().slice(0, 2);

  if (langCode === 'nl') return 'nl';
  if (langCode === 'en') return 'en';
  return 'fr';
}
