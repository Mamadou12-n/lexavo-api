import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, StatusBar,
} from 'react-native';
import { colors } from '../theme/colors';

const TABS = [
  { key: 'cgu', label: 'CGU' },
  { key: 'privacy', label: 'Vie privee' },
];

const CGU_TEXT = `CONDITIONS GENERALES D'UTILISATION
Derniere mise a jour : mars 2026

1. OBJET
Les presentes Conditions Generales d'Utilisation (ci-apres "CGU") regissent l'utilisation de l'application mobile Lexavo (ci-apres "l'Application"), editee et exploitee par Lexavo SRL, ayant son siege social en Belgique.

L'Application est un outil d'aide a la recherche juridique destine aux professionnels du droit et aux citoyens belges.

2. ACCEPTATION DES CGU
L'utilisation de l'Application implique l'acceptation pleine et entiere des presentes CGU. Si vous n'acceptez pas ces conditions, veuillez ne pas utiliser l'Application.

3. NATURE DES INFORMATIONS FOURNIES
3.1. Les informations fournies par l'Application sont a titre informatif uniquement.
3.2. L'Application NE FOURNIT PAS de conseil juridique professionnel.
3.3. Les reponses generees par l'intelligence artificielle sont basees sur une base de donnees juridique et ne constituent en aucun cas un avis juridique personnalise.
3.4. L'utilisateur est invite a consulter un avocat inscrit a un barreau belge pour toute question juridique specifique a sa situation.

4. RESPONSABILITE
4.1. Lexavo SRL ne saurait etre tenue responsable des decisions prises sur la base des informations fournies par l'Application.
4.2. Lexavo SRL ne garantit pas l'exhaustivite, l'exactitude ou l'actualite des informations fournies.
4.3. L'Application est fournie "en l'etat" sans garantie d'aucune sorte.
4.4. En aucun cas, Lexavo SRL ne pourra etre tenue responsable de dommages directs ou indirects resultant de l'utilisation de l'Application.

5. PROPRIETE INTELLECTUELLE
5.1. L'Application, son contenu, sa structure et son code source sont proteges par le droit d'auteur et le droit de la propriete intellectuelle.
5.2. Les sources juridiques (arrets, lois, decrets) proviennent de bases de donnees publiques officielles (HUDOC, EUR-Lex, Juridat, Moniteur belge, etc.).
5.3. Les textes legislatifs et reglementaires ne font pas l'objet de droits d'auteur conformement au droit belge.
5.4. L'utilisateur s'engage a ne pas reproduire, copier ou distribuer le contenu de l'Application a des fins commerciales sans autorisation prealable.

6. DISPONIBILITE DU SERVICE
6.1. Lexavo SRL s'efforce d'assurer la disponibilite de l'Application 24h/24 et 7j/7.
6.2. Lexavo SRL se reserve le droit d'interrompre temporairement le service pour des raisons de maintenance ou de mise a jour.
6.3. Lexavo SRL ne saurait etre tenue responsable des interruptions de service.

7. MODIFICATION DES CGU
Lexavo SRL se reserve le droit de modifier les presentes CGU a tout moment. Les modifications prendront effet des leur publication dans l'Application. L'utilisateur sera informe de toute modification substantielle.

8. DROIT APPLICABLE ET JURIDICTION
Les presentes CGU sont soumises au droit belge. Tout litige relatif a l'interpretation ou a l'execution des presentes CGU sera soumis aux tribunaux competents de Bruxelles, Belgique.

9. CONTACT
Pour toute question relative aux presentes CGU :
Email : legal@lexavo.be
Adresse : Lexavo SRL, Bruxelles, Belgique`;

const PRIVACY_TEXT = `POLITIQUE DE CONFIDENTIALITE
Derniere mise a jour : mars 2026

Conformement au Reglement General sur la Protection des Donnees (RGPD - Reglement (UE) 2016/679) et a la loi belge du 30 juillet 2018 relative a la protection des personnes physiques a l'egard des traitements de donnees a caractere personnel, nous vous informons de ce qui suit :

1. RESPONSABLE DU TRAITEMENT
Lexavo SRL
Siege social : Bruxelles, Belgique
Email du DPO : dpo@lexavo.be

2. DONNEES COLLECTEES
2.1. Donnees fournies directement par l'utilisateur :
   - Adresse email (lors de l'inscription)
   - Langue preferee
   - Parametres de l'application

2.2. Donnees generees par l'utilisation :
   - Questions juridiques posees a l'assistant
   - Historique de recherche
   - Statistiques d'utilisation (nombre de questions, sources consultees)
   - Donnees techniques (type d'appareil, version du systeme d'exploitation)

2.3. Donnees NON collectees :
   - Donnees de localisation precise
   - Contacts telephoniques
   - Donnees biometriques

3. FINALITES DU TRAITEMENT
Les donnees sont traitees pour les finalites suivantes :
   a) Fournir le service d'aide a la recherche juridique
   b) Ameliorer la qualite des reponses de l'intelligence artificielle
   c) Assurer le fonctionnement technique de l'Application
   d) Envoyer des notifications relatives au service (si consentement)
   e) Etablir des statistiques anonymisees d'utilisation

4. BASE JURIDIQUE DU TRAITEMENT
   - Execution du contrat (Art. 6.1.b RGPD) : pour fournir le service
   - Consentement (Art. 6.1.a RGPD) : pour les communications marketing
   - Interet legitime (Art. 6.1.f RGPD) : pour l'amelioration du service

5. DUREE DE CONSERVATION
   - Donnees de compte : duree de l'abonnement + 1 an
   - Historique des questions : 12 mois (sauf suppression manuelle)
   - Donnees analytiques : 24 mois (anonymisees apres 6 mois)
   - Logs techniques : 6 mois

6. PARTAGE DES DONNEES
6.1. Les questions juridiques sont envoyees a Anthropic (fournisseur d'IA Claude) pour le traitement par l'intelligence artificielle. Anthropic est soumis a des obligations contractuelles strictes en matiere de protection des donnees.
6.2. Aucune donnee personnelle n'est vendue a des tiers.
6.3. Les donnees peuvent etre communiquees aux autorites competentes si la loi l'exige.

7. TRANSFERTS INTERNATIONAUX
Les donnees peuvent etre transferees vers les Etats-Unis (serveurs Anthropic). Ces transferts sont encadres par les Clauses Contractuelles Types approuvees par la Commission europeenne.

8. VOS DROITS
Conformement au RGPD, vous disposez des droits suivants :
   a) Droit d'acces (Art. 15) : obtenir une copie de vos donnees
   b) Droit de rectification (Art. 16) : corriger vos donnees inexactes
   c) Droit a l'effacement (Art. 17) : demander la suppression de vos donnees
   d) Droit a la limitation (Art. 18) : limiter le traitement de vos donnees
   e) Droit a la portabilite (Art. 20) : recevoir vos donnees dans un format structure
   f) Droit d'opposition (Art. 21) : vous opposer au traitement de vos donnees
   g) Droit de retirer votre consentement a tout moment

Pour exercer ces droits, contactez notre DPO : dpo@lexavo.be

9. SECURITE DES DONNEES
Nous mettons en oeuvre des mesures techniques et organisationnelles appropriees pour proteger vos donnees :
   - Chiffrement des donnees en transit (TLS 1.3)
   - Stockage local securise sur l'appareil (AsyncStorage chiffre)
   - Acces restreint aux donnees sur les serveurs
   - Audits de securite reguliers

10. COOKIES ET TECHNOLOGIES SIMILAIRES
L'Application mobile n'utilise pas de cookies. Les donnees de session sont stockees localement sur votre appareil via AsyncStorage.

11. MODIFICATIONS
Toute modification de la presente politique sera communiquee aux utilisateurs via l'Application. La date de derniere mise a jour est indiquee en haut du document.

12. RECLAMATION
Vous avez le droit d'introduire une reclamation aupres de l'Autorite de protection des donnees (APD) belge :
   Autorite de protection des donnees
   Rue de la Presse 35, 1000 Bruxelles
   https://www.autoriteprotectiondonnees.be
   contact@apd-gba.be

13. CONTACT DPO
Data Protection Officer
Email : dpo@lexavo.be
Adresse : Lexavo SRL, Bruxelles, Belgique`;

export default function LegalScreen() {
  const [activeTab, setActiveTab] = useState('cgu');

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.background} />

      {/* Tab bar */}
      <View style={styles.tabBar}>
        {TABS.map((tab) => (
          <TouchableOpacity activeOpacity={0.75}
            key={tab.key}
            style={[styles.tab, activeTab === tab.key && styles.tabActive]}
            onPress={() => setActiveTab(tab.key)}
            activeOpacity={0.8}
          >
            <Text
              style={[
                styles.tabText,
                activeTab === tab.key && styles.tabTextActive,
              ]}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={true}
      >
        <View style={styles.card}>
          {activeTab === 'cgu' ? (
            <LegalContent text={CGU_TEXT} />
          ) : (
            <LegalContent text={PRIVACY_TEXT} />
          )}
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Lexavo SRL — Bruxelles, Belgique
          </Text>
          <Text style={styles.footerText}>
            Contact : legal@lexavo.be | DPO : dpo@lexavo.be
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

function LegalContent({ text }) {
  // Parse text into sections for better presentation
  const lines = text.split('\n');
  return (
    <View>
      {lines.map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) return <View key={index} style={styles.spacer} />;

        // Main title (all caps, first line)
        if (index === 0 || (trimmed === trimmed.toUpperCase() && trimmed.length > 10 && !trimmed.startsWith('-'))) {
          return (
            <Text key={index} style={styles.legalTitle}>
              {trimmed}
            </Text>
          );
        }

        // Section headers (numbered: "1. SOMETHING")
        if (/^\d+\.\s+[A-Z]/.test(trimmed)) {
          return (
            <Text key={index} style={styles.legalSectionTitle}>
              {trimmed}
            </Text>
          );
        }

        // Sub-section (numbered: "1.1." or "a)")
        if (/^\d+\.\d+\./.test(trimmed) || /^[a-g]\)/.test(trimmed)) {
          return (
            <Text key={index} style={styles.legalSubSection}>
              {trimmed}
            </Text>
          );
        }

        // Bullet points
        if (trimmed.startsWith('-') || trimmed.startsWith('\u2022')) {
          return (
            <View key={index} style={styles.bulletRow}>
              <Text style={styles.bulletDot}>{'\u2022'}</Text>
              <Text style={styles.bulletText}>{trimmed.replace(/^[-\u2022]\s*/, '')}</Text>
            </View>
          );
        }

        // Date line
        if (trimmed.startsWith('Derniere mise a jour')) {
          return (
            <Text key={index} style={styles.legalDate}>
              {trimmed}
            </Text>
          );
        }

        // Regular paragraph
        return (
          <Text key={index} style={styles.legalParagraph}>
            {trimmed}
          </Text>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },

  // Tab bar
  tabBar: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    paddingHorizontal: 16,
  },
  tab: {
    flex: 1,
    paddingVertical: 14,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabActive: {
    borderBottomColor: colors.primary,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textMuted,
  },
  tabTextActive: {
    color: colors.primary,
    fontWeight: '700',
  },

  // Scroll
  scroll: {
    flex: 1,
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },

  // Card
  card: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 20,
    elevation: 2,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 1,
  },

  // Legal text styles
  legalTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.primaryDark,
    marginBottom: 4,
    textAlign: 'center',
  },
  legalDate: {
    fontSize: 12,
    color: colors.textMuted,
    fontStyle: 'italic',
    textAlign: 'center',
    marginBottom: 16,
  },
  legalSectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.primary,
    marginTop: 16,
    marginBottom: 6,
  },
  legalSubSection: {
    fontSize: 13,
    color: colors.textPrimary,
    lineHeight: 20,
    marginBottom: 4,
    paddingLeft: 12,
  },
  legalParagraph: {
    fontSize: 13,
    color: colors.textPrimary,
    lineHeight: 20,
    marginBottom: 4,
  },
  bulletRow: {
    flexDirection: 'row',
    paddingLeft: 16,
    marginBottom: 4,
  },
  bulletDot: {
    fontSize: 13,
    color: colors.primary,
    marginRight: 8,
    lineHeight: 20,
  },
  bulletText: {
    flex: 1,
    fontSize: 13,
    color: colors.textPrimary,
    lineHeight: 20,
  },
  spacer: {
    height: 6,
  },

  // Footer
  footer: {
    marginTop: 16,
    alignItems: 'center',
    paddingVertical: 12,
  },
  footerText: {
    fontSize: 11,
    color: colors.textMuted,
    textAlign: 'center',
    marginBottom: 2,
  },
});
