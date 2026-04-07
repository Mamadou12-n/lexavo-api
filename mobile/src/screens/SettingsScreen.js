import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { REGION_KEY, logout } from '../api/client';
import { colors } from '../theme/colors';
import { LinearGradient } from 'expo-linear-gradient';

const LEXAVO_ORANGE = '#C45A2D';
const LEXAVO_NAVY   = '#1C2B3A';

const REGIONS = [
  { id: 'bruxelles', flag: '🏙️', label: 'Bruxelles-Capitale' },
  { id: 'wallonie',  flag: '🌿', label: 'Wallonie'  },
  { id: 'flandre',   flag: '🦁', label: 'Flandre'   },
];

export default function SettingsScreen({ navigation }) {
  const [region, setRegion] = useState('bruxelles');

  useEffect(() => {
    AsyncStorage.getItem(REGION_KEY).then((r) => { if (r) setRegion(r); }).catch(() => {});
  }, []);

  const handleRegionChange = async (id) => {
    setRegion(id);
    try { await AsyncStorage.setItem(REGION_KEY, id); } catch (_) {}
  };

  const handleLogout = () => {
    Alert.alert('Déconnexion', 'Voulez-vous vous déconnecter ?', [
      { text: 'Annuler', style: 'cancel' },
      { text: 'Déconnexion', style: 'destructive', onPress: () => logout() },
    ]);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

      <LinearGradient colors={['#0A1628', '#1A3A5C']} style={styles.heroHeader}>
        <Text style={styles.heroEmoji}>&#x2699;&#xFE0F;</Text>
        <Text style={styles.heroTitle}>Paramètres</Text>
        <Text style={styles.heroSub}>Configurez votre expérience Lexavo</Text>
      </LinearGradient>

      {/* ═══ RÉGION ═══ */}
      <Section title="📍 Votre région">
        <Text style={styles.hint}>
          Lexavo adapte ses réponses au droit régional applicable.
        </Text>
        {REGIONS.map((r) => (
          <TouchableOpacity activeOpacity={0.75}
            key={r.id}
            style={[styles.regionBtn, region === r.id && styles.regionBtnActive]}
            onPress={() => handleRegionChange(r.id)}
            activeOpacity={0.8}
          >
            <Text style={styles.regionFlag}>{r.flag}</Text>
            <Text style={[styles.regionLabel, region === r.id && styles.regionLabelActive]}>
              {r.label}
            </Text>
            {region === r.id && <Text style={styles.regionCheck}>✓</Text>}
          </TouchableOpacity>
        ))}
      </Section>

      {/* ═══ ABONNEMENT ═══ */}
      <Section title="⭐ Mon abonnement">
        <MenuItem
          label="Gérer mon abonnement"
          sub="Voir les plans · Changer de formule"
          onPress={() => navigation.navigate('Subscription')}
        />
      </Section>

      {/* ═══ NOTIFICATIONS ═══ */}
      <Section title="🔔 Notifications">
        <MenuItem
          label="Gérer les notifications"
          sub="Alertes légales · Rappels délais"
          onPress={() => navigation.navigate('Notifications')}
        />
      </Section>

      {/* ═══ HISTORIQUE ═══ */}
      <Section title="📜 Historique">
        <MenuItem
          label="Mes conversations"
          sub="Retrouver vos questions précédentes"
          onPress={() => navigation.navigate('History')}
        />
      </Section>

      {/* ═══ ANNUAIRE ═══ */}
      <Section title="👨‍⚖️ Avocats">
        <MenuItem
          label="Annuaire des avocats"
          sub="Trouver un avocat spécialisé"
          onPress={() => navigation.navigate('Lawyers')}
        />
      </Section>

      {/* ═══ LÉGAL ═══ */}
      <Section title="⚖️ Légal & Conformité">
        <MenuItem
          label="📋 Conditions générales (CGU)"
          onPress={() => navigation.navigate('CGU')}
        />
        <MenuItem
          label="🔒 Politique de confidentialité"
          onPress={() => navigation.navigate('Privacy')}
        />
        <MenuItem
          label="ℹ️ Mentions légales"
          onPress={() => navigation.navigate('MentionsLegales')}
          last
        />
        <Text style={styles.rgpdNote}>
          🇧🇪 Conforme RGPD · Droit belge · APD enregistré
        </Text>
      </Section>

      {/* ═══ DISCLAIMER ═══ */}
      <View style={styles.disclaimerCard}>
        <Text style={styles.disclaimerText}>
          ⚖️ Lexavo est un outil d'information juridique. Il ne remplace pas un avocat ni un conseiller juridique professionnel. En cas de litige complexe, consultez un professionnel du droit.
        </Text>
      </View>

      {/* ═══ DÉCONNEXION ═══ */}
      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout} activeOpacity={0.8}>
        <Text style={styles.logoutText}>🚪 Se déconnecter</Text>
      </TouchableOpacity>

      <Text style={styles.footer}>Lexavo SRL — Le droit pour tous</Text>
    </ScrollView>
  );
}

function Section({ title, children }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.sectionBody}>{children}</View>
    </View>
  );
}

function MenuItem({ label, sub, onPress, last }) {
  return (
    <TouchableOpacity
      style={[styles.menuItem, !last && styles.menuItemBorder]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <View style={{ flex: 1 }}>
        <Text style={styles.menuLabel}>{label}</Text>
        {sub && <Text style={styles.menuSub}>{sub}</Text>}
      </View>
      <Text style={styles.menuArrow}>›</Text>
    </TouchableOpacity>
  );
}

function InfoRow({ label, value }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F8FC' },
  content:   { padding: 16, paddingBottom: 40 },

  heroHeader: { borderRadius: 16, padding: 20, marginBottom: 16, alignItems: 'center' },
  heroEmoji: { fontSize: 32, marginBottom: 8 },
  heroTitle: { fontSize: 20, fontWeight: '900', color: '#FFF', letterSpacing: 0.5 },
  heroSub: { fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4, textAlign: 'center' },

  section:      { marginBottom: 20 },
  sectionTitle: { fontSize: 15, fontWeight: '700', color: '#0F1A2E', marginBottom: 10 },
  sectionBody:  {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 14,
    elevation: 2,
    shadowColor: 'rgba(15,25,46,0.06)',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 1,
  },

  hint: { fontSize: 12, color: '#94A3B8', marginBottom: 10, lineHeight: 16 },

  regionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#E8ECF4',
    marginBottom: 8,
    backgroundColor: '#FFF',
  },
  regionBtnActive: { borderColor: LEXAVO_ORANGE, backgroundColor: '#FFF7ED' },
  regionFlag:      { fontSize: 20, marginRight: 12 },
  regionLabel:     { flex: 1, fontSize: 14, fontWeight: '600', color: '#0F1A2E' },
  regionLabelActive: { color: LEXAVO_ORANGE },
  regionCheck:     { fontSize: 16, color: LEXAVO_ORANGE, fontWeight: '700' },

  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
  },
  menuItemBorder: {
    borderBottomWidth: 1,
    borderBottomColor: '#E8ECF4',
  },
  menuLabel: { fontSize: 14, color: '#0F1A2E', fontWeight: '500' },
  menuSub:   { fontSize: 11, color: '#94A3B8', marginTop: 2 },
  menuArrow: { fontSize: 20, color: '#94A3B8' },

  rgpdNote: {
    fontSize: 10,
    color: '#94A3B8',
    textAlign: 'center',
    marginTop: 10,
    fontStyle: 'italic',
  },

  infoRow:   { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  infoLabel: { fontSize: 13, color: '#94A3B8' },
  infoValue: { fontSize: 13, color: '#0F1A2E', fontWeight: '600', flex: 1, textAlign: 'right' },

  logoutBtn: {
    backgroundColor: '#FEF2F2',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#FECACA',
    marginBottom: 16,
  },
  logoutText: { color: '#DC2626', fontSize: 14, fontWeight: '700' },

  disclaimerCard: {
    marginBottom: 20,
    backgroundColor: '#FFFBEB',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#FDE68A',
  },
  disclaimerText: {
    fontSize: 12,
    color: '#92400E',
    textAlign: 'center',
    lineHeight: 18,
  },

  footer: { textAlign: 'center', fontSize: 11, color: '#94A3B8', marginTop: 4 },
});
