import React, { useState, useRef, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, FlatList,
  Dimensions, StatusBar,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { colors } from '../theme/colors';
import { t, getDeviceLanguage } from '../i18n/translations';
import { REGION_KEY } from '../api/client';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const STORAGE_KEYS = {
  ONBOARDING_DONE: '@lexavo_onboarding_done',
  LANGUAGE: '@lexavo_language',
};

const REGIONS = [
  {
    id: 'bruxelles',
    flag: '🏙️',
    label: 'Bruxelles',
    sub: 'Région de Bruxelles-Capitale',
  },
  {
    id: 'wallonie',
    flag: '🌿',
    label: 'Wallonie',
    sub: 'Région wallonne',
  },
  {
    id: 'flandre',
    flag: '🦁',
    label: 'Flandre',
    sub: 'Vlaams Gewest',
  },
];

const LANGUAGES = [
  { code: 'fr', flag: '🇫🇷', label: 'Français' },
  { code: 'nl', flag: '🇳🇱', label: 'Nederlands' },
  { code: 'en', flag: '🇬🇧', label: 'English' },
  { code: 'de', flag: '🇩🇪', label: 'Deutsch' },
  { code: 'ar', flag: '🇦🇪', label: 'العربية' },
  { code: 'tr', flag: '🇹🇷', label: 'Türkçe' },
  { code: 'es', flag: '🇪🇸', label: 'Español' },
  { code: 'pt', flag: '🇵🇹', label: 'Português' },
];

export default function OnboardingScreen({ navigation }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedLang, setSelectedLang] = useState(getDeviceLanguage());
  const [selectedRegion, setSelectedRegion] = useState('bruxelles');
  const flatListRef = useRef(null);

  const goToStep = useCallback((index) => {
    flatListRef.current?.scrollToIndex({ index, animated: true });
    setCurrentStep(index);
  }, []);

  const handleNext = useCallback(() => {
    if (currentStep < 2) {
      goToStep(currentStep + 1);
    }
  }, [currentStep, goToStep]);

  const handleLanguageSelect = useCallback(async (langCode) => {
    setSelectedLang(langCode);
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.LANGUAGE, langCode);
    } catch (_) {}
  }, []);

  const handleRegionSelect = useCallback(async (regionId) => {
    setSelectedRegion(regionId);
    try { await AsyncStorage.setItem(REGION_KEY, regionId); } catch (_) {}
  }, []);

  const handleComplete = useCallback(async () => {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.ONBOARDING_DONE, 'true');
      await AsyncStorage.setItem(STORAGE_KEYS.LANGUAGE, selectedLang);
      await AsyncStorage.setItem(REGION_KEY, selectedRegion);
    } catch (_) {}
    navigation.reset({
      index: 0,
      routes: [{ name: 'Home' }],
    });
  }, [navigation, selectedLang, selectedRegion]);

  const onViewableItemsChanged = useRef(({ viewableItems }) => {
    if (viewableItems.length > 0) {
      setCurrentStep(viewableItems[0].index);
    }
  }).current;

  const viewabilityConfig = useRef({
    itemVisiblePercentThreshold: 50,
  }).current;

  const steps = [
    { key: 'welcome' },
    { key: 'language' },
    { key: 'region' },
    { key: 'disclaimer' },
  ];

  const renderStep = useCallback(({ item }) => {
    switch (item.key) {
      case 'welcome':
        return (
          <View style={styles.stepContainer}>
            <View style={styles.stepContent}>
              <View style={styles.logoContainer}>
                <Text style={styles.logoIcon}>&#x2696;&#xFE0F;</Text>
                <Text style={styles.logoText}>Lexavo</Text>
              </View>
              <Text style={styles.stepTitle}>
                {t('onboarding_title', selectedLang)}
              </Text>
              <Text style={styles.stepSubtitle}>
                {t('onboarding_subtitle', selectedLang)}
              </Text>
              <View style={styles.featureList}>
                <FeatureItem
                  icon="&#x1F4AC;"
                  text="Posez vos questions juridiques en langage naturel"
                />
                <FeatureItem
                  icon="&#x1F4DA;"
                  text="Base de donnees juridique belge complete"
                />
                <FeatureItem
                  icon="&#x1F50D;"
                  text="Recherche intelligente dans 15+ sources officielles"
                />
                <FeatureItem
                  icon="&#x1F1E7;&#x1F1EA;"
                  text="Droit belge, europeen et international"
                />
              </View>
            </View>
            <TouchableOpacity style={styles.primaryBtn} onPress={handleNext} activeOpacity={0.8}>
              <Text style={styles.primaryBtnText}>Commencer</Text>
            </TouchableOpacity>
          </View>
        );

      case 'language':
        return (
          <View style={styles.stepContainer}>
            <View style={styles.stepContent}>
              <Text style={styles.stepIcon}>&#x1F310;</Text>
              <Text style={styles.stepTitle}>
                {t('language', selectedLang)}
              </Text>
              <Text style={styles.stepDescription}>
                Choisissez votre langue preferee. Vous pourrez la modifier dans les parametres.
              </Text>
              <View style={styles.languageGrid}>
                {LANGUAGES.map((lang) => (
                  <TouchableOpacity activeOpacity={0.75}
                    key={lang.code}
                    style={[
                      styles.languageBtn,
                      selectedLang === lang.code && styles.languageBtnActive,
                    ]}
                    onPress={() => handleLanguageSelect(lang.code)}
                    activeOpacity={0.8}
                  >
                    <Text style={styles.languageFlag}>{lang.flag}</Text>
                    <Text
                      style={[
                        styles.languageLabel,
                        selectedLang === lang.code && styles.languageLabelActive,
                      ]}
                    >
                      {lang.label}
                    </Text>
                    {selectedLang === lang.code && (
                      <View style={styles.languageCheck}>
                        <Text style={styles.languageCheckText}>&#x2713;</Text>
                      </View>
                    )}
                  </TouchableOpacity>
                ))}
              </View>
            </View>
            <TouchableOpacity style={styles.primaryBtn} onPress={handleNext} activeOpacity={0.8}>
              <Text style={styles.primaryBtnText}>Continuer</Text>
            </TouchableOpacity>
          </View>
        );

      case 'region':
        return (
          <View style={styles.stepContainer}>
            <View style={styles.stepContent}>
              <Text style={styles.stepIcon}>📍</Text>
              <Text style={styles.stepTitle}>Votre région</Text>
              <Text style={styles.stepDescription}>
                Le droit belge varie selon la région. Lexavo adaptera ses réponses à votre droit régional automatiquement.
              </Text>
              <View style={styles.languageGrid}>
                {REGIONS.map((r) => (
                  <TouchableOpacity activeOpacity={0.75}
                    key={r.id}
                    style={[
                      styles.languageBtn,
                      selectedRegion === r.id && styles.languageBtnActive,
                    ]}
                    onPress={() => handleRegionSelect(r.id)}
                    activeOpacity={0.8}
                  >
                    <Text style={styles.languageFlag}>{r.flag}</Text>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.languageLabel, selectedRegion === r.id && styles.languageLabelActive]}>
                        {r.label}
                      </Text>
                      <Text style={styles.regionSubLabel}>{r.sub}</Text>
                    </View>
                    {selectedRegion === r.id && (
                      <View style={styles.languageCheck}>
                        <Text style={styles.languageCheckText}>✓</Text>
                      </View>
                    )}
                  </TouchableOpacity>
                ))}
              </View>
              <Text style={styles.regionNote}>
                Vous pourrez modifier votre région à tout moment dans les paramètres.
              </Text>
            </View>
            <TouchableOpacity style={styles.primaryBtn} onPress={handleNext} activeOpacity={0.8}>
              <Text style={styles.primaryBtnText}>Continuer</Text>
            </TouchableOpacity>
          </View>
        );

      case 'disclaimer':
        return (
          <View style={styles.stepContainer}>
            <View style={styles.stepContent}>
              <Text style={styles.stepIcon}>&#x26A0;&#xFE0F;</Text>
              <Text style={styles.stepTitle}>Avertissement important</Text>
              <View style={styles.disclaimerBox}>
                <Text style={styles.disclaimerTitle}>
                  Information juridique &#x2260; Conseil juridique
                </Text>
                <Text style={styles.disclaimerText}>
                  Lexavo est un outil d'aide a la recherche juridique. Les informations
                  fournies sont a titre informatif uniquement et ne remplacent en aucun
                  cas l'avis d'un professionnel du droit.
                </Text>
                <View style={styles.disclaimerDivider} />
                <Text style={styles.disclaimerText}>
                  Pour toute question juridique specifique a votre situation, nous vous
                  recommandons de consulter un avocat inscrit a un barreau belge.
                </Text>
              </View>
            </View>
            <TouchableOpacity
              style={styles.primaryBtn}
              onPress={handleComplete}
              activeOpacity={0.8}
            >
              <Text style={styles.primaryBtnText}>J'ai compris</Text>
            </TouchableOpacity>
          </View>
        );

      default:
        return null;
    }
  }, [selectedLang, handleNext, handleLanguageSelect, handleComplete]);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.primaryDark} />

      <FlatList
        ref={flatListRef}
        data={steps}
        renderItem={renderStep}
        keyExtractor={(item) => item.key}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        scrollEventThrottle={16}
        onViewableItemsChanged={onViewableItemsChanged}
        viewabilityConfig={viewabilityConfig}
        getItemLayout={(_, index) => ({
          length: SCREEN_WIDTH,
          offset: SCREEN_WIDTH * index,
          index,
        })}
      />

      {/* Pagination dots */}
      <View style={styles.pagination}>
        {steps.map((_, index) => (
          <View
            key={index}
            style={[
              styles.paginationDot,
              currentStep === index && styles.paginationDotActive,
            ]}
          />
        ))}
      </View>

      {/* Skip button */}
      {currentStep < 2 && (
        <TouchableOpacity activeOpacity={0.75}
          style={styles.skipBtn}
          onPress={() => goToStep(2)}
          activeOpacity={0.7}
        >
          <Text style={styles.skipText}>Passer</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

function FeatureItem({ icon, text }) {
  return (
    <View style={styles.featureItem}>
      <Text style={styles.featureIcon}>{icon}</Text>
      <Text style={styles.featureText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },

  stepContainer: {
    width: SCREEN_WIDTH,
    flex: 1,
    justifyContent: 'space-between',
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 100,
  },
  stepContent: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },

  // Logo
  logoContainer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  logoIcon: {
    fontSize: 60,
    marginBottom: 8,
  },
  logoText: {
    fontSize: 36,
    fontWeight: '800',
    color: colors.primary,
    letterSpacing: 1,
  },

  // Step content
  stepIcon: {
    fontSize: 50,
    marginBottom: 16,
  },
  stepTitle: {
    fontSize: 24,
    fontWeight: '800',
    color: colors.textPrimary,
    textAlign: 'center',
    marginBottom: 8,
  },
  stepSubtitle: {
    fontSize: 15,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 24,
  },
  stepDescription: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 32,
    paddingHorizontal: 10,
  },

  // Features
  featureList: {
    alignSelf: 'stretch',
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  featureIcon: {
    fontSize: 22,
    marginRight: 12,
  },
  featureText: {
    flex: 1,
    fontSize: 13,
    color: colors.textPrimary,
    lineHeight: 18,
  },

  // Language selection
  languageGrid: {
    alignSelf: 'stretch',
    gap: 12,
  },
  languageBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 18,
    borderWidth: 2,
    borderColor: colors.border,
  },
  languageBtnActive: {
    borderColor: colors.primary,
    backgroundColor: '#EEF3FA',
  },
  languageFlag: {
    fontSize: 20,
    fontWeight: '800',
    color: colors.primary,
    marginRight: 14,
    width: 36,
    textAlign: 'center',
  },
  languageLabel: {
    flex: 1,
    fontSize: 16,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  languageLabelActive: {
    color: colors.primary,
    fontWeight: '700',
  },
  languageCheck: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  languageCheckText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '700',
  },

  // Disclaimer
  disclaimerBox: {
    backgroundColor: '#FFFBEB',
    borderRadius: 14,
    padding: 20,
    borderWidth: 1,
    borderColor: '#FDE68A',
    alignSelf: 'stretch',
  },
  disclaimerTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#92400E',
    textAlign: 'center',
    marginBottom: 12,
  },
  disclaimerText: {
    fontSize: 13,
    color: '#78350F',
    lineHeight: 20,
    textAlign: 'center',
  },
  disclaimerDivider: {
    height: 1,
    backgroundColor: '#FDE68A',
    marginVertical: 12,
  },

  // Buttons
  primaryBtn: {
    backgroundColor: colors.primary,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
    alignSelf: 'stretch',
    elevation: 3,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 1,
  },
  primaryBtnText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 0.5,
  },

  // Pagination
  pagination: {
    flexDirection: 'row',
    justifyContent: 'center',
    position: 'absolute',
    bottom: 70,
    left: 0,
    right: 0,
    gap: 8,
  },
  paginationDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.border,
  },
  paginationDotActive: {
    width: 24,
    backgroundColor: colors.primary,
  },

  // Skip
  skipBtn: {
    position: 'absolute',
    top: 50,
    right: 24,
  },
  skipText: {
    fontSize: 14,
    color: colors.textMuted,
    fontWeight: '600',
  },

  // Region
  regionSubLabel: {
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 2,
  },
  regionNote: {
    fontSize: 12,
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: 16,
    fontStyle: 'italic',
  },
});
