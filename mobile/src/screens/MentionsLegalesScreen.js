import React from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, Linking,
} from 'react-native';
import { colors } from '../theme/colors';

export default function MentionsLegalesScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

      <View style={styles.heroBox}>
        <Text style={styles.heroTitle}>Mentions légales</Text>
        <Text style={styles.heroSub}>Conformément à la réglementation belge</Text>
      </View>

      {/* Éditeur */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🏢 Éditeur de l'application</Text>
        {[
          ['Dénomination', 'Lexavo SRL'],
          ['Forme juridique', 'Société à Responsabilité Limitée (SRL)'],
          ['Siège social', 'Bruxelles, Belgique'],
          ['BCE', '[NUMÉRO BCE À COMPLÉTER]'],
          ['N° TVA', 'BE [NUMÉRO TVA À COMPLÉTER]'],
          ['Capital', '[CAPITAL SOCIAL À COMPLÉTER]'],
          ['Directeur de publication', '[NOM DU DIRIGEANT]'],
          ['E-mail', 'contact@lexavo.be'],
        ].map(([label, value]) => (
          <View key={label} style={styles.row}>
            <Text style={styles.rowLabel}>{label}</Text>
            <Text style={styles.rowValue}>{value}</Text>
          </View>
        ))}
      </View>

      {/* Hébergement */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🖥️ Hébergement</Text>
        <Text style={styles.body}>
          L'infrastructure technique de Lexavo est hébergée par des prestataires
          certifiés ISO 27001 situés dans l'Union Européenne.{'\n\n'}
          Backend / API : [HÉBERGEUR À COMPLÉTER]{'\n'}
          Base de données : [HÉBERGEUR À COMPLÉTER]{'\n'}
          Stockage vectoriel : Local (ChromaDB / pgvector)
        </Text>
      </View>

      {/* Activité */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>⚖️ Nature de l'activité</Text>
        <View style={styles.warningBox}>
          <Text style={styles.warningText}>
            Lexavo SRL n'est PAS un cabinet d'avocats et n'exerce pas d'activité
            réglementée au sens de la loi du 13 avril 1995 relative à l'exercice
            de la profession d'avocat.
          </Text>
        </View>
        <Text style={styles.body}>
          Lexavo est un outil technologique d'information juridique. Ses réponses
          n'ont aucune valeur juridique et ne constituent pas des consultations
          juridiques professionnelles.{'\n\n'}
          Code NACE principal : [CODE NACE À COMPLÉTER]
        </Text>
      </View>

      {/* Propriété intellectuelle */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>©️ Propriété intellectuelle</Text>
        <Text style={styles.body}>
          L'ensemble des éléments constituant l'application Lexavo (design, code source,
          textes, logos, marques) sont la propriété exclusive de Lexavo SRL et sont
          protégés par le Code de droit économique belge (Livre XI) et les conventions
          internationales sur la propriété intellectuelle.{'\n\n'}
          Toute reproduction, totale ou partielle, est interdite sans autorisation
          préalable et écrite de Lexavo SRL.{'\n\n'}
          Les données juridiques affichées (arrêts, lois, règlements) proviennent
          de sources officielles publiques et restent la propriété de leurs auteurs
          respectifs (Belgique, UE, Conseil de l'Europe).
        </Text>
      </View>

      {/* Technologies IA */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🤖 Technologie IA utilisée</Text>
        {[
          { name: 'Claude (Anthropic)', desc: 'Modèle de langage pour la génération de réponses juridiques', link: 'https://www.anthropic.com' },
          { name: 'ChromaDB / pgvector', desc: 'Base de données vectorielle pour la recherche sémantique', link: null },
          { name: 'paraphrase-multilingual-MiniLM-L12-v2', desc: 'Modèle d\'embeddings multilingues (Sentence Transformers)', link: null },
        ].map((t, i) => (
          <View key={i} style={styles.techRow}>
            <Text style={styles.techName}>{t.name}</Text>
            <Text style={styles.techDesc}>{t.desc}</Text>
            {t.link && (
              <TouchableOpacity activeOpacity={0.75} onPress={() => Linking.openURL(t.link)}>
                <Text style={styles.techLink}>{t.link}</Text>
              </TouchableOpacity>
            )}
          </View>
        ))}
      </View>

      {/* Sources juridiques */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📚 Sources juridiques indexées</Text>
        <Text style={styles.body}>
          La base de connaissances de Lexavo est construite à partir de sources
          officielles publiques belges et européennes, notamment :{'\n\n'}
          • Juridat (Cour de cassation belge){'\n'}
          • EUR-Lex (CJUE + législation UE){'\n'}
          • HUDOC (Cour européenne des droits de l'homme){'\n'}
          • Moniteur belge (lois, AR, décrets){'\n'}
          • Cour constitutionnelle belge{'\n'}
          • Conseil d'État belge{'\n'}
          • APD (décisions RGPD belges){'\n'}
          • Et 9 autres sources officielles
        </Text>
      </View>

      {/* Contact */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📬 Contact</Text>
        {[
          ['Général', 'contact@lexavo.be'],
          ['Légal / DPO', 'privacy@lexavo.be'],
          ['Support', 'support@lexavo.be'],
        ].map(([type, email]) => (
          <TouchableOpacity activeOpacity={0.75}
            key={type}
            style={styles.contactRow}
            onPress={() => Linking.openURL(`mailto:${email}`)}
          >
            <Text style={styles.contactType}>{type}</Text>
            <Text style={styles.contactEmail}>{email}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Mentions légales Lexavo SRL · Version 1.0 · Mars 2026{'\n'}
          Droit applicable : droit belge
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
  heroTitle: { fontSize: 16, fontWeight: '800', color: '#FFF' },
  heroSub:   { fontSize: 11, color: 'rgba(255,255,255,0.6)', marginTop: 4 },

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
  cardTitle: { fontSize: 13, fontWeight: '800', color: '#1C2B3A', marginBottom: 10 },
  body:      { fontSize: 12, color: colors.textPrimary, lineHeight: 18 },

  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    flexWrap: 'wrap',
    gap: 4,
  },
  rowLabel: { fontSize: 11, color: colors.textMuted, flex: 1 },
  rowValue: { fontSize: 11, fontWeight: '600', color: colors.textPrimary, flex: 2, textAlign: 'right' },

  warningBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#FCA5A5',
  },
  warningText: { fontSize: 11, color: '#991B1B', lineHeight: 17, fontWeight: '600' },

  techRow: { marginBottom: 10, paddingBottom: 10, borderBottomWidth: 1, borderBottomColor: colors.border },
  techName: { fontSize: 12, fontWeight: '700', color: colors.textPrimary },
  techDesc: { fontSize: 11, color: colors.textSecondary, marginTop: 2 },
  techLink: { fontSize: 10, color: '#2980B9', marginTop: 2, textDecorationLine: 'underline' },

  contactRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: 10,
    marginBottom: 6,
  },
  contactType:  { fontSize: 12, color: colors.textSecondary, fontWeight: '600' },
  contactEmail: { fontSize: 12, color: '#2980B9', textDecorationLine: 'underline' },

  footer: {
    backgroundColor: '#FFFBEB',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#FDE68A',
  },
  footerText: { fontSize: 10, color: '#92400E', textAlign: 'center', lineHeight: 15, fontStyle: 'italic' },
});
