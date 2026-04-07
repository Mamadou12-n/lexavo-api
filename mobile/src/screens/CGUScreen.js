import React from 'react';
import { View, Text, ScrollView, StyleSheet, Platform } from 'react-native';
import { colors } from '../theme/colors';

const SECTIONS = [
  {
    title: '1. Objet et champ d\'application',
    body: `Les présentes Conditions Générales d'Utilisation (CGU) régissent l'accès et l'utilisation de l'application mobile Lexavo, éditée par Lexavo SRL (ci-après « Lexavo »).

En téléchargeant, installant ou utilisant l'application, vous acceptez sans réserve les présentes CGU. Si vous n'acceptez pas ces conditions, vous devez cesser immédiatement toute utilisation de l'application.`,
  },
  {
    title: '2. Description du service',
    body: `Lexavo est un outil d'information juridique basé sur l'intelligence artificielle, conçu pour fournir des informations générales sur le droit belge (droit du travail, droit civil, droit fiscal, etc.).

L'application utilise des modèles de langage (Claude d'Anthropic) et une base de données documentaire issue de sources officielles belges (Juridat, EUR-Lex, HUDOC, Moniteur belge, etc.) pour générer des réponses informatives.`,
  },
  {
    title: '3. Avertissement important — Pas de consultation juridique',
    body: `⚠️ AVERTISSEMENT ESSENTIEL

Les informations et réponses générées par Lexavo ont une valeur INFORMATIVE UNIQUEMENT. Elles ne constituent en aucun cas :
• Une consultation juridique au sens de la loi du 13 avril 1995 relative à l'exercice de la profession d'avocat ;
• Un avis juridique professionnel ;
• Une représentation en justice.

Pour toute décision juridique importante, vous devez consulter un avocat inscrit au barreau.`,
  },
  {
    title: '4. Conditions d\'accès',
    body: `L'utilisation de Lexavo est réservée aux personnes majeures (18 ans ou plus) ou aux personnes morales agissant par l'intermédiaire d'un représentant légal habilité.

Vous vous engagez à utiliser l'application de manière licite et conforme aux présentes CGU, et à ne pas l'utiliser pour des fins contraires à l'ordre public ou aux bonnes mœurs.`,
  },
  {
    title: '5. Responsabilité',
    body: `Lexavo SRL s'efforce de fournir des informations exactes et à jour, mais ne garantit pas l'exhaustivité, l'exactitude ou l'actualité des informations fournies.

Lexavo SRL ne peut être tenu responsable :
• Des décisions prises sur base des informations fournies par l'application ;
• Des erreurs ou omissions dans les réponses générées ;
• Des préjudices directs ou indirects résultant de l'utilisation de l'application ;
• Des interruptions ou indisponibilités du service.

La responsabilité de Lexavo SRL est limitée au montant payé par l'utilisateur pour l'abonnement au cours des 12 derniers mois.`,
  },
  {
    title: '6. Propriété intellectuelle',
    body: `L'application Lexavo, son contenu, son code source, ses marques et ses éléments graphiques sont la propriété exclusive de Lexavo SRL et sont protégés par le droit belge et européen de la propriété intellectuelle.

Toute reproduction, représentation, modification ou distribution, sans autorisation préalable et écrite de Lexavo SRL, est strictement interdite.

Les sources juridiques utilisées (arrêts, lois, règlements) sont des documents officiels de droit public et ne font pas l'objet de droits exclusifs de Lexavo SRL.`,
  },
  {
    title: '7. Abonnements et paiements',
    body: `Certaines fonctionnalités de Lexavo sont disponibles via abonnement payant. Les conditions tarifaires, les modalités de paiement et les conditions d'annulation sont détaillées dans la section "Abonnement" de l'application.

Les paiements sont traités par des prestataires de paiement certifiés (Stripe). Lexavo SRL ne stocke aucune donnée de paiement.

Conformément au Livre VI du Code de droit économique, vous bénéficiez d'un droit de rétractation de 14 jours calendrier pour tout achat en ligne.`,
  },
  {
    title: '8. Modification des CGU',
    body: `Lexavo SRL se réserve le droit de modifier les présentes CGU à tout moment. Les modifications entrent en vigueur dès leur publication dans l'application. En continuant à utiliser l'application après notification des modifications, vous acceptez les nouvelles CGU.`,
  },
  {
    title: '9. Droit applicable et juridiction',
    body: `Les présentes CGU sont régies par le droit belge.

En cas de litige relatif à l'interprétation ou à l'exécution des présentes CGU, les parties s'engagent à rechercher une solution amiable. À défaut, les tribunaux de l'arrondissement judiciaire de Bruxelles seront seuls compétents.

Ces CGU sont rédigées en langue française. En cas de traduction dans une autre langue, la version française fait foi.`,
  },
  {
    title: '10. Contact',
    body: `Pour toute question relative aux présentes CGU :

E-mail : legal@lexavo.be
Adresse : Lexavo SRL, Bruxelles, Belgique
BCE : [NUMÉRO BCE À COMPLÉTER]

Dernière mise à jour : 31 mars 2026`,
  },
];

export default function CGUScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.heroBox}>
        <Text style={styles.heroTitle}>Conditions Générales d'Utilisation</Text>
        <Text style={styles.heroSub}>Lexavo SRL · Version 1.0 · Mars 2026</Text>
        <View style={styles.legalPill}>
          <Text style={styles.legalPillText}>Droit belge · Tribunaux de Bruxelles</Text>
        </View>
      </View>

      {SECTIONS.map((s, i) => (
        <View key={i} style={styles.section}>
          <Text style={styles.sectionTitle}>{s.title}</Text>
          <Text style={styles.sectionBody}>{s.body}</Text>
        </View>
      ))}

      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Ces CGU ont été rédigées conformément au droit belge et au droit européen de la consommation.
          Elles ont été mises à jour le 31 mars 2026.
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
    marginBottom: 16,
    alignItems: 'center',
  },
  heroTitle: { fontSize: 16, fontWeight: '800', color: '#FFF', textAlign: 'center', marginBottom: 6 },
  heroSub:   { fontSize: 11, color: 'rgba(255,255,255,0.65)', marginBottom: 10 },
  legalPill: {
    backgroundColor: 'rgba(196,90,45,0.3)',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 4,
  },
  legalPillText: { fontSize: 10, color: '#C45A2D', fontWeight: '700' },

  section: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    elevation: 1,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 1,
  },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: '#1C2B3A', marginBottom: 8 },
  sectionBody:  { fontSize: 12, color: colors.textPrimary, lineHeight: 19 },

  footer: {
    backgroundColor: '#FFFBEB',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#FDE68A',
    marginTop: 6,
  },
  footerText: { fontSize: 10, color: '#92400E', fontStyle: 'italic', textAlign: 'center', lineHeight: 15 },
});
