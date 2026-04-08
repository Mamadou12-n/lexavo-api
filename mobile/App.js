/**
 * App Droit Belgique — Lexavo
 * Application mobile React Native / Expo
 *
 * Flux de démarrage :
 *   1. Onboarding (1ère ouverture uniquement)
 *   2. Consentement RGPD (si pas encore accepté)
 *   3. Authentification JWT (si pas de token stocké)
 *   4. Application principale
 *
 * Architecture :
 *   Bottom Tab Navigator (5 onglets)
 *   ├── 🏠 Accueil      → HomeScreen        (branding + outils + quota)
 *   ├── 💬 Chat IA      → AskScreen         (RAG Q&A avec Claude)
 *   ├── ⚖️  Avocats     → LawyerScreen      (annuaire avocats)
 *   ├── ⭐ Abonnement   → SubscriptionScreen (7 plans tarifaires)
 *   └── ⚙️  Reglages    → SettingsStack      (parametres, legal)
 *
 *   Defend reste accessible via la grille Outils de HomeScreen.
 */

import React, { useEffect, useState } from 'react';
import { Platform, Text } from 'react-native';
import AsyncStorage                    from '@react-native-async-storage/async-storage';
import { NavigationContainer }         from '@react-navigation/native';
import { createBottomTabNavigator }    from '@react-navigation/bottom-tabs';
import { createStackNavigator }        from '@react-navigation/stack';
import { SafeAreaProvider }            from 'react-native-safe-area-context';

// Original screens
import HomeScreen     from './src/screens/HomeScreen';
import AskScreen      from './src/screens/AskScreen';
import SettingsScreen from './src/screens/SettingsScreen';

// 7 outils particuliers + Campus
import ShieldScreen        from './src/screens/ShieldScreen';
import CalculateursScreen  from './src/screens/CalculateursScreen';
import DiagnosticScreen    from './src/screens/DiagnosticScreen';
import MatchScreen         from './src/screens/MatchScreen';
import EmergencyScreen     from './src/screens/EmergencyScreen';
import FiscalScreen        from './src/screens/FiscalScreen';
import DefendScreen        from './src/screens/DefendScreen';
import StudentScreen       from './src/screens/StudentScreen';

// Legal + Subscription + Notifications + History + Lawyers screens
import SubscriptionScreen    from './src/screens/SubscriptionScreen';
import NotificationsScreen   from './src/screens/NotificationsScreen';
import HistoryScreen         from './src/screens/HistoryScreen';
import LawyerScreen          from './src/screens/LawyerScreen';
import CGUScreen             from './src/screens/CGUScreen';
import PrivacyScreen         from './src/screens/PrivacyScreen';
import MentionsLegalesScreen from './src/screens/MentionsLegalesScreen';

// Auth + Onboarding screens
import AuthScreen      from './src/screens/AuthScreen';
import OnboardingScreen from './src/screens/OnboardingScreen';

// RGPD consent modal
import ConsentModal, { CONSENT_KEY } from './src/components/ConsentModal';

import { colors }                        from './src/theme/colors';
import { initApiUrl, initAuthToken, setUnauthHandler, logout,
         registerPushToken }             from './src/api/client';
import { registerForPushNotifications }  from './src/utils/notifications';
import { LanguageProvider, useLanguage } from './src/context/LanguageContext';

const LEXAVO_ORANGE = '#C45A2D';
const LEXAVO_NAVY   = '#1C2B3A';

const ONBOARDING_KEY = '@lexavo_onboarding_done';

const Tab            = createBottomTabNavigator();
const LexavoStackNav = createStackNavigator();
const SettingsNav    = createStackNavigator();

const STACK_SCREEN_OPTIONS = {
  headerStyle:      { backgroundColor: LEXAVO_NAVY },
  headerTintColor:  '#FFF',
  headerTitleStyle: { fontWeight: '700', fontSize: 15 },
  cardStyle:        { backgroundColor: colors.background },
};

// Lexavo stack navigator — 7 outils essentiels particuliers
function LexavoStack() {
  return (
    <LexavoStackNav.Navigator screenOptions={STACK_SCREEN_OPTIONS}>
      <LexavoStackNav.Screen name="Defend"       component={DefendScreen}       options={{ headerTitle: '⚡ Contester' }} />
      <LexavoStackNav.Screen name="Shield"       component={ShieldScreen}       options={{ headerTitle: '📄 Analyser un document' }} />
      <LexavoStackNav.Screen name="Diagnostic"   component={DiagnosticScreen}   options={{ headerTitle: '🔬 Diagnostic juridique' }} />
      <LexavoStackNav.Screen name="Calculateurs" component={CalculateursScreen} options={{ headerTitle: '🧮 Calculateurs juridiques' }} />
      <LexavoStackNav.Screen name="Match"        component={MatchScreen}        options={{ headerTitle: '🤝 Trouver un avocat' }} />
      <LexavoStackNav.Screen name="Emergency"    component={EmergencyScreen}    options={{ headerTitle: '🚨 Urgence 24h' }} />
      <LexavoStackNav.Screen name="Fiscal"       component={FiscalScreen}       options={{ headerTitle: '💰 Questions fiscales' }} />
    </LexavoStackNav.Navigator>
  );
}

// Settings stack navigator — réglages + tous les écrans secondaires
function SettingsStack() {
  return (
    <SettingsNav.Navigator screenOptions={STACK_SCREEN_OPTIONS}>
      <SettingsNav.Screen name="SettingsMain"    component={SettingsScreen}        options={{ headerTitle: '⚙️  Réglages' }} />
      <SettingsNav.Screen name="Subscription"    component={SubscriptionScreen}    options={{ headerTitle: '⭐ Abonnement' }} />
      <SettingsNav.Screen name="Notifications"   component={NotificationsScreen}   options={{ headerTitle: '🔔 Notifications' }} />
      <SettingsNav.Screen name="History"         component={HistoryScreen}         options={{ headerTitle: '📜 Historique des conversations' }} />
      <SettingsNav.Screen name="Lawyers"         component={LawyerScreen}          options={{ headerTitle: '👨‍⚖️ Annuaire des avocats' }} />
      <SettingsNav.Screen name="CGU"             component={CGUScreen}             options={{ headerTitle: "📋 Conditions d'utilisation" }} />
      <SettingsNav.Screen name="Privacy"         component={PrivacyScreen}         options={{ headerTitle: '🔒 Politique de confidentialité' }} />
      <SettingsNav.Screen name="MentionsLegales" component={MentionsLegalesScreen} options={{ headerTitle: 'ℹ️  Mentions légales' }} />
    </SettingsNav.Navigator>
  );
}

// Application principale (5 onglets — Defend accessible via grille Outils)
function MainApp() {
  const { t } = useLanguage();
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={({ route }) => ({
          tabBarActiveTintColor:   LEXAVO_ORANGE,
          tabBarInactiveTintColor: colors.textMuted,
          tabBarStyle: {
            backgroundColor: colors.surface,
            borderTopColor:  colors.border,
            paddingBottom:   Platform.OS === 'ios' ? 20 : 8,
            paddingTop:      6,
            height:          Platform.OS === 'ios' ? 85 : 65,
          },
          tabBarLabelStyle: {
            fontSize: 9,
            fontWeight: '600',
          },
          headerStyle: {
            backgroundColor: LEXAVO_NAVY,
          },
          headerTintColor: '#FFF',
          headerTitleStyle: {
            fontWeight: '700',
            fontSize: 16,
          },
        })}
      >
        {/* ── 1. Accueil ── */}
        <Tab.Screen
          name="Home"
          component={HomeScreen}
          options={{
            headerTitle: '⚖️  Lexavo',
            tabBarLabel: t('tab_home'),
            tabBarIcon: () => <Text style={{ fontSize: 20 }}>🏠</Text>,
          }}
        />
        {/* ── 2. Campus ── */}
        <Tab.Screen
          name="Campus"
          component={StudentScreen}
          options={{
            headerTitle: '🎓 Lexavo Campus',
            tabBarLabel: t('tab_campus'),
            tabBarIcon: () => <Text style={{ fontSize: 20 }}>🎓</Text>,
          }}
        />
        {/* ── 3. Chat IA ── */}
        <Tab.Screen
          name="Ask"
          component={AskScreen}
          options={{
            headerTitle: '💬 Chat juridique IA',
            tabBarLabel: t('tab_chat'),
            tabBarIcon: () => <Text style={{ fontSize: 20 }}>💬</Text>,
          }}
        />
        {/* ── 4. Abonnement ── */}
        <Tab.Screen
          name="Abonnement"
          component={SubscriptionScreen}
          options={{
            headerTitle: '⭐ Abonnement',
            headerStyle: { backgroundColor: LEXAVO_NAVY },
            headerTintColor: '#FFF',
            tabBarLabel: t('tab_abo'),
            tabBarIcon: () => <Text style={{ fontSize: 20 }}>⭐</Text>,
          }}
        />
        {/* ── 5. Réglages ── */}
        <Tab.Screen
          name="Settings"
          component={SettingsStack}
          options={{
            headerShown: false,
            tabBarLabel: t('tab_more'),
            tabBarIcon: () => <Text style={{ fontSize: 20 }}>⚙️</Text>,
          }}
        />
        {/* ── Outils (caché, navigation interne depuis HomeScreen) ── */}
        <Tab.Screen
          name="Outils"
          component={LexavoStack}
          options={{
            headerShown: false,
            tabBarButton: () => null,
          }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  // null = loading | 'onboarding' | 'consent' | 'auth' | 'main'
  const [appState, setAppState] = useState(null);

  useEffect(() => {
    bootstrap();
  }, []);

  async function bootstrap() {
    try {
      await initApiUrl();

      // 1. Onboarding — une seule fois
      const onboardingDone = await AsyncStorage.getItem(ONBOARDING_KEY);
      if (!onboardingDone) {
        setAppState('onboarding');
        return;
      }

      // 2. Consentement RGPD
      const consent = await AsyncStorage.getItem(CONSENT_KEY);
      if (consent !== 'accepted') {
        setAppState('consent');
        return;
      }

      // 3. Auth JWT
      const hasToken = await initAuthToken();
      if (!hasToken) {
        setAppState('auth');
        return;
      }

      // 4. Application principale — enregistrer le token push
      setAppState('main');
      registerForPushNotifications()
        .then((token) => { if (token) registerPushToken(token).catch(() => {}); })
        .catch(() => {});
    } catch (e) {
      console.warn('Bootstrap error:', e);
      setAppState('onboarding');
    }
  }

  // Intercepteur 401 → retour à l'écran de connexion
  useEffect(() => {
    setUnauthHandler(() => setAppState('auth'));
  }, []);

  // Splash silencieuse pendant le chargement
  if (appState === null) return null;

  // ─── Onboarding ──────────────────────────────────────────────────────────────
  if (appState === 'onboarding') {
    return (
      <SafeAreaProvider>
        <OnboardingScreen
          onDone={async () => {
            await AsyncStorage.setItem(ONBOARDING_KEY, '1');
            const consent = await AsyncStorage.getItem(CONSENT_KEY);
            if (consent !== 'accepted') {
              setAppState('consent');
            } else {
              const hasToken = await initAuthToken();
              setAppState(hasToken ? 'main' : 'auth');
            }
          }}
        />
      </SafeAreaProvider>
    );
  }

  // ─── Consentement RGPD ────────────────────────────────────────────────────────
  if (appState === 'consent') {
    return (
      <SafeAreaProvider>
        <ConsentModal
          visible={true}
          onAccept={async () => {
            const hasToken = await initAuthToken();
            setAppState(hasToken ? 'main' : 'auth');
          }}
        />
      </SafeAreaProvider>
    );
  }

  // ─── Authentification ─────────────────────────────────────────────────────────
  if (appState === 'auth') {
    return (
      <SafeAreaProvider>
        <AuthScreen
          onAuthSuccess={async () => {
            registerForPushNotifications()
              .then((token) => { if (token) registerPushToken(token).catch(() => {}); })
              .catch(() => {});
            setAppState('main');
          }}
        />
      </SafeAreaProvider>
    );
  }

  // ─── Application principale ───────────────────────────────────────────────────
  return (
    <LanguageProvider>
      <SafeAreaProvider>
        <MainApp />
      </SafeAreaProvider>
    </LanguageProvider>
  );
}
