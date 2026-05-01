# Lexavo Mobile — Journal des erreurs Expo Go

## Contexte
- App : Lexavo Mobile (React Native + Expo SDK 54)
- Mode test : Expo Go via tunnel ngrok + LAN
- IP LAN : `192.168.1.9:8082`
- URL tunnel : `https://mg90zdm-anonymous-8082.exp.direct`

---

## Erreurs rencontrées (chronologique)

### Erreur 1 — `Runtime not ready: Exception in HostFunction: <unknown>`
- **Symptôme** : crash au démarrage dans Expo Go, avant rendu écran
- **Source** : Hermes/JSI runtime, exception lors de l'appel d'un module natif
- **Diagnostic Metro** : visible dans logs après bundling Android+iOS

### Erreur 2 — `App entry not found / The app entry point named "main" was not registered`
- **Symptôme** : Expo Go affiche page d'erreur avec ce message
- **Source** : `registerRootComponent(App)` dans `index.js` n'a pas été exécuté
- **Cause probable** : exception au top-level d'un import → `index.js` interrompu

### Erreur 3 — `There was a problem running the requested app`
- **Symptôme** : Expo Go affiche message générique
- **Cause** : tunnel ngrok déconnecté + bundle inaccessible

### Erreur 4 — Écran tout noir
- **Symptôme** : app charge mais rien ne s'affiche, écran noir persistant
- **Cause** : bundle exécute mais App() throw silencieusement OU `return null` permanent

---

## Fixes tentés (échoués individuellement)

### Fix 1 — App.js Rules of Hooks
- **Bug réel** : `if (!fontsLoaded) return null;` placé AVANT `useEffect(() => { bootstrap() }, [])`
- **Action** : déplacé après tous les hooks
- **Résultat** : bug corrigé mais erreur persiste

### Fix 2 — Notifications.setNotificationHandler au top-level
- **Bug réel** : appel direct au top-level de `utils/notifications.js`
- **Action** : encapsulé dans `initNotificationHandler()` appelé depuis useEffect
- **Résultat** : bug corrigé mais erreur persiste

### Fix 3 — API expo-notifications obsolète
- **Bug réel** : `shouldShowAlert` déprécié SDK 54
- **Action** : remplacé par `shouldShowBanner` + `shouldShowList`
- **Résultat** : warning supprimé mais erreur persiste

### Fix 4 — newArchEnabled à false
- **Action** : `app.json` → `"newArchEnabled": false`
- **Résultat** : warning Expo Go ("New Arch always enabled in Expo Go") → reverted à true
- **Résultat final** : aucun effet sur l'erreur

### Fix 5 — react-native-worklets manquant
- **Bug réel** : reanimated 4.x sur SDK 54 nécessite `react-native-worklets`
- **Action** : `npx expo install react-native-worklets` + `babel.config.js` plugin updated
- **Résultat** : worklets bien installé, bundle compile, mais erreur persiste

### Fix 6 — expo install --fix
- **Action** : `npx expo install --fix` (versions packages alignées SDK 54.0.34)
- **Résultat** : versions corrigées, bundle compile, erreur persiste

---

## Approche Phase 4.5 (systematic-debugging) — Architecture suspecte

Après 6 fixes échoués, signal architectural. **Stop fixes individuels** → **isolation par App.js minimal**.

### Test isolation
- App.js réduit à un simple `<View><Text>LEXAVO</Text></View>`
- Zéro hook Expo, zéro screen, zéro reanimated
- Bundle : 4.7 MB (vs 11.6 MB version complète)

### Si écran s'affiche correctement
→ React Native + Expo Go fonctionnent
→ Cause = un des imports/screens de l'App complet
→ Réintroduire incrémentalement pour identifier

### Si écran noir persiste
→ Problème config plus profond (app.json, package.json, native modules)
→ Investiguer config Expo + plugins

---

## État actuel (2026-05-01)

- ✅ react-native-worklets installé + plugin babel
- ✅ Notifications.setNotificationHandler hors top-level
- ✅ Rules of Hooks respectées App.js
- ✅ Versions packages SDK 54.0.34 alignées
- 🧪 App.js minimal en cours de test pour isoler
- 🔍 En attente résultat utilisateur sur écran minimal

---

## Configuration projet pour debug

| Fichier | État |
|---------|:----:|
| `mobile/App.js` | **VERSION MINIMALE** (test isolation) |
| `mobile/App.full.js.backup` | Backup version complète |
| `mobile/babel.config.js` | `react-native-worklets/plugin` |
| `mobile/app.json` | `newArchEnabled: true` |
| `mobile/src/utils/notifications.js` | `initNotificationHandler()` exporté |
| `mobile/package.json` | `react-native-worklets@^x.x.x` ajouté |
