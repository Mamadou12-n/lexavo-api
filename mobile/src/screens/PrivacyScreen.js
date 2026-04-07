import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Linking } from 'react-native';
import { colors } from '../theme/colors';

const RIGHTS = [
  { icon: '👁️', right: 'Accès', desc: 'Obtenir une copie de vos données personnelles traitées par Lexavo.' },
  { icon: '✏️', right: 'Rectification', desc: 'Corriger des données inexactes ou incomplètes vous concernant.' },
  { icon: '🗑️', right: 'Effacement', desc: 'Demander la suppression de vos données ("droit à l\'oubli").' },
  { icon: '📦', right: 'Portabilité', desc: 'Recevoir vos données dans un format structuré et lisible par machine.' },
  { icon: '🚫', right: 'Opposition', desc: 'Vous opposer au traitement de vos données pour des motifs légitimes.' },
  { icon: '⏸️', right: 'Limitation', desc: 'Demander la limitation du traitement dans certains cas.' },
];

const DATA_COLLECTED = [
  { category: 'Questions juridiques', data: 'Texte des questions posées à l\'IA', basis: 'Intérêt légitime (Art. 6.1.f)', retention: 'Session uniquement (non stockées)' },
  { category: 'E-mail (Emergency)', data: 'Adresse e-mail fournie volontairement', basis: 'Consentement (Art. 6.1.a)', retention: '12 mois après la dernière interaction' },
  { category: 'Données techniques', data: 'Logs d\'erreur anonymisés', basis: 'Intérêt légitime (Art. 6.1.f)', retention: '90 jours' },
  { category: 'Préférences app', data: 'URL API, consentement (local)', basis: 'Exécution du contrat (Art. 6.1.b)', retention: 'Jusqu\'à désinstallation' },
];

export default function PrivacyScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

      <View style={styles.heroBox}>
        <Text style={styles.heroIcon}>🔒</Text>
        <Text style={styles.heroTitle}>Politique de confidentialité</Text>
        <Text style={styles.heroSub}>Conforme RGPD (Règlement UE 2016/679){'\n'}Loi belge du 30 juillet 2018</Text>
      </View>

      {/* Responsable du traitement */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>👤 Responsable du traitement</Text>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Société</Text>
          <Text style={styles.infoValue}>Lexavo SRL</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Siège</Text>
          <Text style={styles.infoValue}>Bruxelles, Belgique</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>BCE</Text>
          <Text style={styles.infoValue}>[NUMÉRO BCE]</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>DPO</Text>
          <Text style={styles.infoValue}>privacy@lexavo.be</Text>
        </View>
      </View>

      {/* Données collectées */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📊 Données collectées et traitées</Text>
        {DATA_COLLECTED.map((d, i) => (
          <View key={i} style={styles.dataRow}>
            <Text style={styles.dataCat}>{d.category}</Text>
            <Text style={styles.dataDetail}>• Données : {d.data}</Text>
            <Text style={styles.dataDetail}>• Base légale : {d.basis}</Text>
            <Text style={styles.dataDetail}>• Conservation : {d.retention}</Text>
          </View>
        ))}
      </View>

      {/* Tiers et transferts */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🌐 Tiers et transferts internationaux</Text>
        <View style={styles.thirdPartyRow}>
          <Text style={styles.thirdPartyName}>Anthropic (USA)</Text>
          <Text style={styles.thirdPartyDesc}>
            Les questions posées à l'IA sont traitées via l'API Claude d'Anthropic.
            Ce transfert hors UE est encadré par des Clauses Contractuelles Types (SCC)
            conformément à l'Art. 46 RGPD.{'\n'}
            Politique Anthropic : www.anthropic.com/privacy
          </Text>
        </View>
        <View style={[styles.thirdPartyRow, { marginTop: 10 }]}>
          <Text style={styles.thirdPartyName}>Stripe (USA/IE)</Text>
          <Text style={styles.thirdPartyDesc}>
            Traitement des paiements (si applicable). Stripe est certifié PCI-DSS.
            Lexavo ne stocke aucune donnée de paiement.
          </Text>
        </View>
        <Text style={styles.noSaleText}>
          🛡️ Vos données ne sont jamais vendues, partagées à des fins publicitaires,
          ni cédées à des tiers non mentionnés ci-dessus.
        </Text>
      </View>

      {/* Droits */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>⚖️ Vos droits (RGPD Art. 15-22)</Text>
        {RIGHTS.map((r, i) => (
          <View key={i} style={styles.rightRow}>
            <Text style={styles.rightIcon}>{r.icon}</Text>
            <View style={styles.rightContent}>
              <Text style={styles.rightName}>Droit de {r.right}</Text>
              <Text style={styles.rightDesc}>{r.desc}</Text>
            </View>
          </View>
        ))}
        <View style={styles.exerciseBox}>
          <Text style={styles.exerciseTitle}>Comment exercer vos droits :</Text>
          <Text style={styles.exerciseText}>
            Envoyez un e-mail à <Text style={styles.emailLink}>privacy@lexavo.be</Text>
            {' '}avec une copie de votre pièce d'identité.
            Réponse garantie dans les 30 jours (Art. 12 RGPD).
          </Text>
        </View>
      </View>

      {/* APD */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🏛️ Droit de réclamation</Text>
        <Text style={styles.body}>
          Vous avez le droit d'introduire une réclamation auprès de l'Autorité de Protection
          des Données (APD), l'autorité de contrôle belge :
        </Text>
        <TouchableOpacity activeOpacity={0.75}
          style={styles.apdBtn}
          onPress={() => Linking.openURL('https://www.autoriteprotectiondonnees.be')}
        >
          <Text style={styles.apdBtnText}>🔗 www.autoriteprotectiondonnees.be</Text>
        </TouchableOpacity>
        <Text style={styles.body}>Rue de la Presse 35 · 1000 Bruxelles · +32 2 274 48 00</Text>
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Politique de confidentialité Lexavo SRL · Version 1.0{'\n'}
          Dernière mise à jour : 31 mars 2026{'\n'}
          Toute modification sera notifiée dans l'application.
        </Text>
      </View>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content:   { padding: 16, paddingBottom: 40 },

  heroBox: {
    backgroundColor: '#1C2B3A',
    borderRadius: 16,
    padding: 20,
    marginBottom: 14,
    alignItems: 'center',
  },
  heroIcon:  { fontSize: 32, marginBottom: 8 },
  heroTitle: { fontSize: 16, fontWeight: '800', color: '#FFF', textAlign: 'center', marginBottom: 6 },
  heroSub:   { fontSize: 11, color: 'rgba(255,255,255,0.65)', textAlign: 'center', lineHeight: 17 },

  card: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 14,
    marginBottom: 12,
    elevation: 2,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 1,
  },
  cardTitle: { fontSize: 13, fontWeight: '800', color: '#1C2B3A', marginBottom: 12 },

  infoRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6, borderBottomWidth: 1, borderBottomColor: colors.border, paddingBottom: 6 },
  infoLabel: { fontSize: 12, color: colors.textMuted },
  infoValue: { fontSize: 12, fontWeight: '600', color: colors.textPrimary },

  dataRow: {
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
  },
  dataCat:    { fontSize: 12, fontWeight: '700', color: '#1C2B3A', marginBottom: 4 },
  dataDetail: { fontSize: 11, color: colors.textSecondary, lineHeight: 17 },

  thirdPartyRow: {
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: 10,
  },
  thirdPartyName: { fontSize: 12, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 },
  thirdPartyDesc: { fontSize: 11, color: colors.textSecondary, lineHeight: 17 },
  noSaleText: {
    marginTop: 10,
    fontSize: 11,
    color: '#065F46',
    backgroundColor: '#D1FAE5',
    borderRadius: 8,
    padding: 8,
    lineHeight: 17,
  },

  rightRow: { flexDirection: 'row', gap: 10, marginBottom: 10, alignItems: 'flex-start' },
  rightIcon: { fontSize: 16, marginTop: 1 },
  rightContent: { flex: 1 },
  rightName: { fontSize: 12, fontWeight: '700', color: colors.textPrimary },
  rightDesc: { fontSize: 11, color: colors.textSecondary, lineHeight: 16, marginTop: 2 },

  exerciseBox: {
    backgroundColor: '#EFF6FF',
    borderRadius: 8,
    padding: 10,
    marginTop: 4,
    borderWidth: 1,
    borderColor: '#BFDBFE',
  },
  exerciseTitle: { fontSize: 11, fontWeight: '700', color: '#1D4ED8', marginBottom: 4 },
  exerciseText:  { fontSize: 11, color: '#1E40AF', lineHeight: 17 },
  emailLink:     { fontWeight: '700', textDecorationLine: 'underline' },

  body: { fontSize: 12, color: colors.textPrimary, lineHeight: 18, marginBottom: 8 },

  apdBtn: {
    backgroundColor: '#EFF6FF',
    borderRadius: 8,
    padding: 10,
    marginVertical: 6,
    alignItems: 'center',
  },
  apdBtnText: { fontSize: 12, color: '#1D4ED8', fontWeight: '600' },

  footer: {
    backgroundColor: '#FFFBEB',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#FDE68A',
    marginTop: 4,
  },
  footerText: { fontSize: 10, color: '#92400E', textAlign: 'center', lineHeight: 15, fontStyle: 'italic' },
});
