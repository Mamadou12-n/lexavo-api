import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { REGION_KEY, logout } from '../api/client';
import { colors } from '../theme/colors';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useLanguage } from '../context/LanguageContext';

const LEXAVO_ORANGE = colors.brand;
const LEXAVO_NAVY   = colors.brandNavy;

const REGION_DEFS = [
  { id: 'bruxelles', flag: '🏙️', labelKey: 'region_bxl_long' },
  { id: 'wallonie',  flag: '🌿', labelKey: 'region_wal' },
  { id: 'flandre',   flag: '🦁', labelKey: 'region_fla' },
];

export default function SettingsScreen({ navigation }) {
  const { t } = useLanguage();
  const [region, setRegion] = useState('bruxelles');

  useEffect(() => {
    AsyncStorage.getItem(REGION_KEY).then((r) => { if (r) setRegion(r); }).catch(() => {});
  }, []);

  const handleRegionChange = async (id) => {
    setRegion(id);
    try { await AsyncStorage.setItem(REGION_KEY, id); } catch (_) {}
  };

  const handleLogout = () => {
    Alert.alert(t('set_logout_confirm_title'), t('set_logout_confirm_msg'), [
      { text: t('common_cancel'), style: 'cancel' },
      { text: t('set_logout'), style: 'destructive', onPress: () => logout() },
    ]);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

      <LinearGradient colors={[colors.brandNavy, colors.brandNavyLight]} style={styles.heroHeader}>
        <Ionicons name="settings-outline" size={32} color="#FFF" style={{ marginBottom: 8 }} accessibilityElementsHidden />
        <Text style={styles.heroTitle}>{t('set_title')}</Text>
        <Text style={styles.heroSub}>{t('set_sub')}</Text>
      </LinearGradient>

      {/* ═══ RÉGION ═══ */}
      <Section title={t('set_section_region')}>
        <Text style={styles.hint}>{t('set_region_hint')}</Text>
        {REGION_DEFS.map((r) => {
          const label = t(r.labelKey);
          return (
            <TouchableOpacity activeOpacity={0.75}
              key={r.id}
              style={[styles.regionBtn, region === r.id && styles.regionBtnActive]}
              onPress={() => handleRegionChange(r.id)}
              activeOpacity={0.8}
              accessible={true}
              accessibilityRole="button"
              accessibilityLabel={label}
              accessibilityState={{ selected: region === r.id }}
            >
              <Text style={styles.regionFlag}>{r.flag}</Text>
              <Text style={[styles.regionLabel, region === r.id && styles.regionLabelActive]}>
                {label}
              </Text>
              {region === r.id && <Text style={styles.regionCheck}>✓</Text>}
            </TouchableOpacity>
          );
        })}
      </Section>

      {/* ═══ ABONNEMENT ═══ */}
      <Section title={t('set_section_sub')}>
        <MenuItem
          label={t('set_manage_sub')}
          sub={t('set_manage_sub_hint')}
          onPress={() => navigation.navigate('Subscription')}
        />
      </Section>

      {/* ═══ NOTIFICATIONS ═══ */}
      <Section title={t('set_section_notif')}>
        <MenuItem
          label={t('set_manage_notif')}
          sub={t('set_manage_notif_hint')}
          onPress={() => navigation.navigate('Notifications')}
        />
      </Section>

      {/* ═══ HISTORIQUE ═══ */}
      <Section title={t('set_section_history')}>
        <MenuItem
          label={t('set_history')}
          sub={t('set_history_hint')}
          onPress={() => navigation.navigate('History')}
        />
      </Section>

      {/* ═══ ANNUAIRE ═══ */}
      <Section title={t('set_section_lawyers')}>
        <MenuItem
          label={t('set_lawyers')}
          sub={t('set_lawyers_hint')}
          onPress={() => navigation.navigate('Lawyers')}
        />
      </Section>

      {/* ═══ LÉGAL ═══ */}
      <Section title={t('set_section_legal')}>
        <MenuItem
          label={t('set_cgu')}
          onPress={() => navigation.navigate('CGU')}
        />
        <MenuItem
          label={t('set_privacy')}
          onPress={() => navigation.navigate('Privacy')}
        />
        <MenuItem
          label={t('set_mentions')}
          onPress={() => navigation.navigate('MentionsLegales')}
          last
        />
        <Text style={styles.rgpdNote}>{t('set_rgpd_note')}</Text>
      </Section>

      {/* ═══ DISCLAIMER ═══ */}
      <View style={styles.disclaimerCard}>
        <Text style={styles.disclaimerText}>{t('disclaimer_long')}</Text>
      </View>

      {/* ═══ DÉCONNEXION ═══ */}
      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout} activeOpacity={0.8} accessible={true} accessibilityRole="button" accessibilityLabel={t('set_logout')}>
        <Text style={styles.logoutText}>{t('set_logout')}</Text>
      </TouchableOpacity>

      <Text style={styles.footer}>{t('set_footer')}</Text>
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
      accessible={true}
      accessibilityRole="button"
      accessibilityLabel={typeof label === 'string' ? label : 'Élément de menu'}
      accessibilityHint={sub}
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
