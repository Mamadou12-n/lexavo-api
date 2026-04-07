import React, { useState } from 'react';
import {
  Modal, View, Text, ScrollView, TouchableOpacity, StyleSheet, Platform,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export const CONSENT_KEY = 'lexavo_consent_v1';

export async function hasConsent() {
  const v = await AsyncStorage.getItem(CONSENT_KEY);
  return v === 'accepted';
}

export default function ConsentModal({ visible, onAccept }) {
  const [scrolledToBottom, setScrolledToBottom] = useState(false);

  const handleAccept = async () => {
    await AsyncStorage.setItem(CONSENT_KEY, 'accepted');
    onAccept();
  };

  const handleScroll = ({ nativeEvent }) => {
    const { layoutMeasurement, contentOffset, contentSize } = nativeEvent;
    const isBottom = layoutMeasurement.height + contentOffset.y >= contentSize.height - 40;
    if (isBottom) setScrolledToBottom(true);
  };

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet">
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.logo}>LEXAVO</Text>
          <Text style={styles.subtitle}>Avant de commencer</Text>
        </View>

        <ScrollView
          style={styles.scrollArea}
          contentContainerStyle={styles.scrollContent}
          onScroll={handleScroll}
          scrollEventThrottle={100}
          showsVerticalScrollIndicator
        >
          <Text style={styles.sectionTitle}>📋 Conditions d'utilisation</Text>
          <Text style={styles.body}>
            Lexavo est un outil d'information juridique basé sur l'intelligence artificielle.
            Les réponses générées ont une valeur informative uniquement et ne constituent
            pas des consultations juridiques professionnelles.{'\n\n'}
            En utilisant Lexavo, vous reconnaissez que :{'\n'}
            • Les informations fournies ne remplacent pas l'avis d'un avocat qualifié.{'\n'}
            • Lexavo SRL ne peut être tenu responsable des décisions prises sur base
              des réponses de l'application.{'\n'}
            • Le droit belge applicable et les tribunaux compétents sont ceux de Bruxelles.
          </Text>

          <Text style={[styles.sectionTitle, { marginTop: 20 }]}>🔒 Protection des données (RGPD)</Text>
          <Text style={styles.body}>
            Conformément au Règlement (UE) 2016/679 (RGPD) et à la loi belge du 30 juillet 2018,
            Lexavo SRL traite vos données personnelles dans le respect strict de votre vie privée.{'\n\n'}
            <Text style={styles.bold}>Données collectées :</Text>{'\n'}
            • Questions posées à l'application (traitées via l'API Anthropic){'\n'}
            • Adresse e-mail (uniquement si vous utilisez Emergency/urgences){'\n'}
            • Données de configuration (URL API — stockées localement){'\n\n'}
            <Text style={styles.bold}>Vos droits :</Text>{'\n'}
            • Droit d'accès, de rectification et d'effacement de vos données{'\n'}
            • Droit à la portabilité et à l'opposition{'\n'}
            • Droit d'introduire une réclamation auprès de l'APD
              (www.autoriteprotectiondonnees.be){'\n\n'}
            <Text style={styles.bold}>Contact DPO :</Text> privacy@lexavo.be{'\n\n'}
            Vos données ne sont jamais vendues à des tiers.
            Les échanges avec l'IA transitent par les serveurs d'Anthropic (USA)
            conformément aux clauses contractuelles types de l'UE (SCC).
          </Text>

          <Text style={[styles.sectionTitle, { marginTop: 20 }]}>ℹ️ Informations légales</Text>
          <Text style={styles.body}>
            Éditeur : Lexavo SRL{'\n'}
            Siège social : Bruxelles, Belgique{'\n'}
            BCE : [NUMÉRO BCE À COMPLÉTER]{'\n'}
            E-mail : contact@lexavo.be{'\n\n'}
            Lexavo n'est pas un cabinet d'avocats et n'exerce pas d'activité réglementée.
          </Text>

          <View style={styles.scrollHint}>
            <Text style={styles.scrollHintText}>
              ↓ Faites défiler jusqu'en bas pour accepter
            </Text>
          </View>
        </ScrollView>

        {/* Footer */}
        <View style={styles.footer}>
          <TouchableOpacity activeOpacity={0.75}
            style={[styles.acceptBtn, !scrolledToBottom && styles.acceptBtnDisabled]}
            onPress={handleAccept}
            disabled={!scrolledToBottom}
          >
            <Text style={styles.acceptBtnText}>
              {scrolledToBottom ? '✅  J\'accepte les conditions' : 'Lisez jusqu\'en bas pour continuer'}
            </Text>
          </TouchableOpacity>
          <Text style={styles.footerNote}>
            Version 1.0 · Conforme RGPD · Droit belge
          </Text>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAFBFC' },

  header: {
    backgroundColor: '#1C2B3A',
    paddingTop: Platform.OS === 'ios' ? 60 : 40,
    paddingBottom: 20,
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  logo:     { fontSize: 24, fontWeight: '900', color: '#C45A2D', letterSpacing: 4 },
  subtitle: { fontSize: 13, color: 'rgba(255,255,255,0.75)', marginTop: 4 },

  scrollArea:   { flex: 1 },
  scrollContent: { padding: 20, paddingBottom: 10 },

  sectionTitle: { fontSize: 14, fontWeight: '800', color: '#1C2B3A', marginBottom: 8 },
  body:         { fontSize: 13, color: '#374151', lineHeight: 21 },
  bold:         { fontWeight: '700' },

  scrollHint: { alignItems: 'center', paddingVertical: 16 },
  scrollHintText: { fontSize: 11, color: '#9CA3AF', fontStyle: 'italic' },

  footer: {
    padding: 20,
    paddingBottom: Platform.OS === 'ios' ? 36 : 20,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    backgroundColor: '#FFF',
  },
  acceptBtn: {
    backgroundColor: '#1C2B3A',
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 8,
  },
  acceptBtnDisabled: { backgroundColor: '#9CA3AF' },
  acceptBtnText: { color: '#FFF', fontSize: 15, fontWeight: '700' },
  footerNote: { textAlign: 'center', fontSize: 10, color: '#9CA3AF' },
});
