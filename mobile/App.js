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

// Lexavo hub + 15 feature screens
import LexavoHomeScreen    from './src/screens/LexavoHomeScreen';
import ShieldScreen        from './src/screens/ShieldScreen';
import CalculateursScreen  from './src/screens/CalculateursScreen';
import ContratsScreen      from './src/screens/ContratsScreen';
import ReponsesScreen      from './src/screens/ReponsesScreen';
import DiagnosticScreen    from './src/screens/DiagnosticScreen';
import ScoreScreen         from './src/screens/ScoreScreen';
import ComplianceScreen    from './src/screens/ComplianceScreen';
import AlertesScreen       from './src/screens/AlertesScreen';
// DecodeScreen supprime — fusionne dans ShieldScreen (DocumentScreen)
import LitigesScreen       from './src/screens/LitigesScreen';
import MatchScreen         from './src/screens/MatchScreen';
import EmergencyScreen     from './src/screens/EmergencyScreen';
import ProofScreen         from './src/screens/ProofScreen';
import HeritageScreen      from './src/screens/HeritageScreen';
import FiscalScreen        from './src/screens/FiscalScreen';
import DefendScreen        from './src/screens/DefendScreen';
import StudentScreen       from './src/screens/StudentScreen';
// AuditScreen supprime — fusionne dans ComplianceScreen (Audit Entreprise)

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

// Lexavo stack navigator — hub + all 15 feature screens
function LexavoStack() {
  return (
    <LexavoStackNav.Navigator screenOptions={STACK_SCREEN_OPTIONS}>
      <LexavoStackNav.Screen name="LexavoHome"   component={LexavoHomeScreen}    options={{ headerTitle: '⚖️  Outils juridiques' }} />
      <LexavoStackNav.Screen name="Defend"      component={DefendScreen}        options={{ headerTitle: '⚡ Defend — Contestation' }} />
      <LexavoStackNav.Screen name="Shield"       component={ShieldScreen}        options={{ headerTitle: '📄 Analyseur de documents' }} />
      <LexavoStackNav.Screen name="Calculateurs" component={CalculateursScreen}  options={{ headerTitle: '🧮 Calculateurs juridiques' }} />
      <LexavoStackNav.Screen name="Contrats"     component={ContratsScreen}      options={{ headerTitle: '📝 Contrats — Génération PDF' }} />
      <LexavoStackNav.Screen name="Reponses"     component={ReponsesScreen}      options={{ headerTitle: '✉️  Réponses juridiques' }} />
      <LexavoStackNav.Screen name="Diagnostic"   component={DiagnosticScreen}    options={{ headerTitle: '🔬 Diagnostic juridique' }} />
      <LexavoStackNav.Screen name="Score"        component={ScoreScreen}         options={{ headerTitle: '📊 Score — Santé juridique' }} />
      <LexavoStackNav.Screen name="Compliance"   component={ComplianceScreen}    options={{ headerTitle: '🏢 Audit Entreprise' }} />
      <LexavoStackNav.Screen name="Alertes"      component={AlertesScreen}       options={{ headerTitle: '🔔 Alertes législatives' }} />
      {/* Decode supprime — fusionne dans Shield (DocumentScreen) */}
      <LexavoStackNav.Screen name="Litiges"      component={LitigesScreen}       options={{ headerTitle: '⚖️  Litiges — Recouvrement' }} />
      <LexavoStackNav.Screen name="Match"        component={MatchScreen}         options={{ headerTitle: '🤝 Match — Trouver un avocat' }} />
      <LexavoStackNav.Screen name="Emergency"    component={EmergencyScreen}     options={{ headerTitle: '🚨 Emergency — Urgence 24h' }} />
      <LexavoStackNav.Screen name="Proof"        component={ProofScreen}         options={{ headerTitle: '🗂️  Proof — Dossier de preuves' }} />
      <LexavoStackNav.Screen name="Heritage"     component={HeritageScreen}      options={{ headerTitle: '🏛️  Héritage — Succession' }} />
      <LexavoStackNav.Screen name="Fiscal"       component={FiscalScreen}        options={{ headerTitle: '💰 Fiscal — Questions fiscales' }} />
      <LexavoStackNav.Screen name="Student"      component={StudentScreen}       options={{ headerTitle: '🎓 Étudiants — Quiz & Révision' }} />
      {/* Audit supprime — fusionne dans Compliance (Audit Entreprise) */}
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
            tabBarLabel: 'Accueil',
            tabBarIcon: () => <Text style={{ fontSize: 20 }}>🏠</Text>,
          }}
        />
        {/* ── 2. Chat IA ── */}
        <Tab.Screen
          name="Ask"
          component={AskScreen}
          options={{
            headerTitle: '💬 Chat juridique IA',
            tabBarLabel: 'Chat',
            tabBarIcon: () => <Text style={{ fontSize: 20 }}>💬</Text>,
          }}
        />
        {/* ── 3. Avocats ── */}
        <Tab.Screen
          name="Avocats"
          component={LawyerScreen}
          options={{
            headerTitle: '⚖️ Annuaire des avocats',
            headerStyle: { backgroundColor: LEXAVO_NAVY },
            headerTintColor: '#FFF',
            tabBarLabel: 'Avocats',
            tabBarIcon: () => <Text style={{ fontSize: 20 }}>⚖️</Text>,
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
            tabBarLabel: 'Abo',
            tabBarIcon: () => <Text style={{ fontSize: 20 }}>⭐</Text>,
          }}
        />
        {/* ── 5. Reglages ── */}
        <Tab.Screen
          name="Settings"
          component={SettingsStack}
          options={{
            headerShown: false,
            tabBarLabel: 'Settings',
            tabBarIcon: () => <Text style={{ fontSize: 20 }}>⚙️</Text>,
          }}
        />
        {/* ── Outils (caché, navigation interne) ── */}
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
    <SafeAreaProvider>
      <MainApp />
    </SafeAreaProvider>
  );
}
