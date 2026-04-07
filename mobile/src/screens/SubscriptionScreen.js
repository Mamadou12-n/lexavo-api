/**
 * SubscriptionScreen — Lexavo
 * 6 tiers tarifaires + toggle mensuel/annuel + badge beta.
 * Prix en .99 — pricing psychologique.
 */

import React, { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, Linking, Alert, Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect } from '@react-navigation/native';
import {
  getSubscriptionStatus,
  createCheckoutSession,
  cancelSubscription,
  restoreSubscription,
  getCachedUser,
} from '../api/client';
import { colors } from '../theme/colors';

const NAVY   = '#1C2B3A';
const ORANGE = '#C45A2D';
const PRO_BG = '#1A3A5C';
const GREEN  = '#27AE60';
const { width: SCREEN_W } = Dimensions.get('window');

// ─── Plans alignes sur le backend ──────────────────────────────────────────
const PLANS = [
  {
    id: 'free',
    name: 'Lexavo Free',
    subtitle: 'Etudiants en droit',
    emoji: '🎓',
    monthly: 0,
    annual: 0,
    highlight: false,
    badge: null,
    features: [
      { ok: true,  label: '3 questions / mois' },
      { ok: true,  label: 'Recherche vectorielle' },
      { ok: true,  label: 'Acces a la base juridique' },
      { ok: true,  label: 'Lexavo Score' },
      { ok: false, label: 'Chat IA illimite' },
      { ok: false, label: 'Analyse de contrats' },
      { ok: false, label: 'Generation de documents' },
    ],
  },
  {
    id: 'basic',
    name: 'Lexavo Basic',
    subtitle: 'Particuliers',
    emoji: '👤',
    monthly: 4.99,
    annual: 49.99,
    foundingPrice: 3.99,
    highlight: false,
    badge: 'Accessible',
    features: [
      { ok: true, label: 'Chat IA illimite' },
      { ok: true, label: '15 branches du droit' },
      { ok: true, label: '3 modeles de contrats / mois' },
      { ok: true, label: 'Alertes legislatives de base' },
      { ok: true, label: 'Lexavo Score' },
      { ok: true, label: 'Historique complet' },
      { ok: false, label: 'Analyse de contrats (Shield)' },
      { ok: false, label: 'Support prioritaire' },
    ],
  },
  {
    id: 'pro',
    name: 'Lexavo Pro',
    subtitle: 'Avocats & juristes',
    emoji: '⚖️',
    monthly: 49.99,
    annual: 499.99,
    foundingPrice: 39.99,
    highlight: true,
    badge: 'Populaire',
    features: [
      { ok: true, label: 'Tout Basic inclus' },
      { ok: true, label: 'Base documentaire complete' },
      { ok: true, label: 'Documents illimites' },
      { ok: true, label: 'Analyse de contrats (Shield)' },
      { ok: true, label: 'Label Avocat certifie' },
      { ok: true, label: 'Leads qualifies' },
      { ok: true, label: 'Statistiques profil' },
      { ok: true, label: 'Support prioritaire (48h)' },
    ],
  },
  {
    id: 'business',
    name: 'Lexavo Business',
    subtitle: 'PME (jusqu\'a 5 utilisateurs)',
    emoji: '🏢',
    monthly: 79.99,
    annual: 799.99,
    foundingPrice: 59.99,
    highlight: false,
    badge: 'Equipe',
    features: [
      { ok: true, label: 'Tout Pro inclus' },
      { ok: true, label: 'Jusqu\'a 5 utilisateurs' },
      { ok: true, label: 'Contrats illimites' },
      { ok: true, label: 'Alertes RGPD & conformite' },
      { ok: true, label: 'Export PDF & rapports' },
      { ok: true, label: 'Support prioritaire' },
    ],
  },
  {
    id: 'firm_s',
    name: 'Lexavo Firm',
    subtitle: 'Petit cabinet (2-10 avocats)',
    emoji: '🏛️',
    monthly: 149.99,
    annual: null, // sur devis
    highlight: false,
    badge: 'Cabinets',
    features: [
      { ok: true, label: 'Tout Business inclus' },
      { ok: true, label: 'Jusqu\'a 10 utilisateurs' },
      { ok: true, label: 'Documents marque (logo)' },
      { ok: true, label: 'Gestion dossiers' },
      { ok: true, label: 'Onboarding inclus' },
      { ok: true, label: 'Support dedie' },
    ],
  },
  {
    id: 'firm_m',
    name: 'Lexavo Firm+',
    subtitle: 'Cabinet moyen (10-30)',
    emoji: '🏛️',
    monthly: 299.99,
    annual: null,
    highlight: false,
    badge: 'Cabinets+',
    features: [
      { ok: true, label: 'Tout Firm inclus' },
      { ok: true, label: 'Jusqu\'a 30 utilisateurs' },
      { ok: true, label: 'API acces complet' },
      { ok: true, label: 'Integrations sur mesure' },
      { ok: true, label: 'Account manager dedie' },
    ],
  },
  {
    id: 'enterprise',
    name: 'Lexavo Enterprise',
    subtitle: 'Grandes entreprises',
    emoji: '🌐',
    monthly: -1, // sur devis
    annual: null,
    highlight: false,
    badge: 'Sur mesure',
    features: [
      { ok: true, label: 'Tout Firm+ inclus' },
      { ok: true, label: 'Utilisateurs illimites' },
      { ok: true, label: 'SLA garanti' },
      { ok: true, label: 'Deploiement on-premise' },
      { ok: true, label: 'Support 24/7' },
    ],
  },
];

export default function SubscriptionScreen() {
  const [status, setStatus]         = useState(null);
  const [user, setUser]             = useState(null);
  const [loading, setLoading]       = useState(true);
  const [actionPlan, setActionPlan] = useState(null);
  const [error, setError]           = useState(null);
  const [billing, setBilling]       = useState('monthly'); // monthly | annual

  useFocusEffect(
    useCallback(() => {
      let active = true;
      setLoading(true);
      setError(null);

      Promise.all([getSubscriptionStatus(), getCachedUser()])
        .then(([sub, u]) => {
          if (!active) return;
          setStatus(sub);
          setUser(u);
        })
        .catch((e) => {
          if (!active) return;
          setError(e.response?.data?.detail || e.message || 'Impossible de charger l\'abonnement.');
        })
        .finally(() => { if (active) setLoading(false); });

      return () => { active = false; };
    }, [])
  );

  const subscribe = async (planId) => {
    if (planId === 'enterprise') {
      Alert.alert(
        'Lexavo Enterprise',
        'Contactez-nous a contact@lexavo.be pour un devis sur mesure.',
      );
      return;
    }
    setActionPlan(planId);
    setError(null);
    try {
      const data = await createCheckoutSession(planId, billing);
      if (data.checkout_url) {
        await Linking.openURL(data.checkout_url);
      }
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Impossible d\'ouvrir le paiement.');
    } finally {
      setActionPlan(null);
    }
  };

  const handleCancel = () => {
    Alert.alert(
      'Annuler l\'abonnement',
      'Vous gardez l\'acces jusqu\'a la fin de la periode en cours.',
      [
        { text: 'Non', style: 'cancel' },
        {
          text: 'Oui, annuler',
          style: 'destructive',
          onPress: async () => {
            try {
              await cancelSubscription();
              Alert.alert('Annulation confirmee', 'Votre abonnement reste actif jusqu\'en fin de periode.');
              const updated = await getSubscriptionStatus();
              setStatus(updated);
            } catch (e) {
              setError(e.response?.data?.detail || e.message);
            }
          },
        },
      ]
    );
  };

  const handleRestore = async () => {
    setLoading(true);
    try {
      await restoreSubscription();
      const updated = await getSubscriptionStatus();
      setStatus(updated);
      Alert.alert('Abonnement reactive', `Plan ${updated.plan} actif.`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const currentPlanId = status?.plan ?? 'free';
  const isBeta = status?.beta ?? false;

  const formatPrice = (plan) => {
    const price = billing === 'annual' && plan.annual
      ? plan.annual
      : plan.monthly;
    if (price === 0)  return 'Gratuit';
    if (price === -1) return 'Sur devis';
    const suffix = billing === 'annual' ? ' / an' : ' / mois';
    return `${price.toFixed(2).replace('.', ',')}€${suffix}`;
  };

  if (loading && !status) {
    return (
      <View style={styles.centerLoad}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>

      {/* Hero gradient */}
      <LinearGradient colors={['#0A1628', '#1A3A5C']} style={styles.hero}>
        <Text style={styles.heroEmoji}>{'\u2696\uFE0F'}</Text>
        <Text style={styles.heroTitle}>Choisissez votre plan</Text>
        <Text style={styles.heroSub}>Investissez dans votre s{'\u00E9'}curit{'\u00E9'} juridique</Text>
        {user && (
          <Text style={styles.heroEmail}>{user.email}</Text>
        )}
        {status && (
          <View style={styles.currentPlanBadge}>
            <Text style={styles.currentPlanText}>
              Plan actuel : {PLANS.find(p => p.id === currentPlanId)?.name ?? currentPlanId}
              {status.current_period_end
                ? ` \u00B7 actif jusqu'au ${status.current_period_end.slice(0, 10)}`
                : ''}
            </Text>
          </View>
        )}
      </LinearGradient>

      {/* Beta banner — date volontairement cachee, notification par email J-30 */}
      {isBeta && (
        <View style={styles.betaBanner}>
          <Text style={styles.betaTitle}>🎉 Acces complet offert</Text>
          <Text style={styles.betaText}>
            Profitez de toutes les fonctionnalites Lexavo gratuitement.{'\n'}
            Pas de carte bancaire requise.
          </Text>
        </View>
      )}

      {/* Billing toggle */}
      <View style={styles.toggleContainer}>
        <TouchableOpacity activeOpacity={0.75}
          style={[styles.togglePill, billing === 'monthly' && styles.togglePillActive]}
          onPress={() => setBilling('monthly')}
        >
          <Text style={[styles.toggleText, billing === 'monthly' && styles.toggleTextActive]}>
            Mensuel
          </Text>
        </TouchableOpacity>
        <TouchableOpacity activeOpacity={0.75}
          style={[styles.togglePill, billing === 'annual' && styles.togglePillActive]}
          onPress={() => setBilling('annual')}
        >
          <Text style={[styles.toggleText, billing === 'annual' && styles.toggleTextActive]}>
            Annuel
          </Text>
          <LinearGradient colors={['#FF6B6B', '#FFB84D']} style={styles.savePill}>
            <Text style={styles.saveText}>-17%</Text>
          </LinearGradient>
        </TouchableOpacity>
      </View>

      {/* Quota */}
      {status && status.questions_limit !== -1 && !isBeta && (
        <View style={styles.quotaBar}>
          <Text style={styles.quotaLabel}>
            {status.questions_used} / {status.questions_limit} questions ce mois
          </Text>
          <View style={styles.quotaTrack}>
            <View style={[
              styles.quotaFill,
              {
                width: `${Math.min(100, (status.questions_used / status.questions_limit) * 100)}%`,
                backgroundColor: status.questions_used >= status.questions_limit ? colors.error : colors.primary,
              },
            ]} />
          </View>
        </View>
      )}

      {/* Error */}
      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      {/* Plan cards */}
      {PLANS.map((plan) => {
        const isCurrent = plan.id === currentPlanId;
        const isLoading = actionPlan === plan.id;
        const priceLabel = formatPrice(plan);
        const isEnterprise = plan.id === 'enterprise';

        const cardContent = (
          <>
            {plan.badge && (
              <View style={[styles.badge, plan.highlight && styles.badgeHighlight]}>
                <Text style={[styles.badgeText, plan.highlight && styles.badgeTextHighlight]}>
                  {plan.badge}
                </Text>
              </View>
            )}

            <View style={styles.planHeader}>
              <Text style={styles.planEmoji}>{plan.emoji}</Text>
              <View style={styles.planInfo}>
                <Text style={[styles.planName, plan.highlight && styles.planNameHighlight]}>
                  {plan.name}
                </Text>
                <Text style={[styles.planSubtitle, plan.highlight && { color: 'rgba(255,255,255,0.6)' }]}>
                  {plan.subtitle}
                </Text>
                <Text style={[styles.planPrice, plan.highlight && styles.planPriceHighlight]}>
                  {priceLabel}
                </Text>
              </View>
              {isCurrent && (
                <View style={styles.activePill}>
                  <Text style={styles.activePillText}>Actif</Text>
                </View>
              )}
            </View>

            {/* Founding member price during beta */}
            {isBeta && plan.foundingPrice && (
              <View style={styles.foundingBox}>
                <Text style={styles.foundingText}>
                  {'\u{1F396}'} Founding Member : {plan.foundingPrice.toFixed(2).replace('.', ',')}€/mois a vie
                </Text>
              </View>
            )}

            <View style={styles.featureList}>
              {plan.features.map((f, i) => (
                <View key={i} style={styles.featureRow}>
                  <View style={[styles.featureDot, f.ok ? styles.featureDotOk : styles.featureDotNo]} />
                  <Text style={[styles.featureText, !f.ok && styles.featureTextOff,
                    plan.highlight && f.ok && { color: '#FFF' },
                    plan.highlight && !f.ok && { color: 'rgba(255,255,255,0.35)' },
                  ]}>
                    {f.label}
                  </Text>
                </View>
              ))}
            </View>

            {/* CTA */}
            {!isCurrent && plan.id !== 'free' && (
              <TouchableOpacity activeOpacity={0.75}
                onPress={() => subscribe(plan.id)}
                disabled={!!actionPlan}
              >
                {isLoading
                  ? <View style={styles.subscribeBtnFallback}><ActivityIndicator color="#FFF" /></View>
                  : <LinearGradient
                      colors={plan.highlight ? ['#6C3FA0', '#8B5CF6'] : ['#1A3A5C', '#2A5A8C']}
                      start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
                      style={styles.subscribeBtn}
                    >
                      <Text style={styles.subscribeBtnText}>
                        {isEnterprise ? 'Nous contacter' : `Souscrire \u2014 ${priceLabel}`}
                      </Text>
                    </LinearGradient>
                }
              </TouchableOpacity>
            )}

            {isCurrent && plan.id !== 'free' && (
              <TouchableOpacity activeOpacity={0.75} style={styles.cancelBtn} onPress={handleCancel}>
                <Text style={styles.cancelBtnText}>Gerer / Annuler l'abonnement</Text>
              </TouchableOpacity>
            )}
          </>
        );

        return plan.highlight ? (
          <LinearGradient
            key={plan.id}
            colors={['#6C3FA0', '#C45A2D', '#FFB84D']}
            start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
            style={[styles.planCardGradientBorder, isCurrent && { borderColor: GREEN, borderWidth: 2 }]}
          >
            <View style={styles.planCardInner}>
              {cardContent}
            </View>
          </LinearGradient>
        ) : (
          <View
            key={plan.id}
            style={[
              styles.planCard,
              isCurrent && styles.planCardCurrent,
            ]}
          >
            {cardContent}
          </View>
        );
      })}

      {/* Legal */}
      <View style={styles.legalBox}>
        <Text style={styles.legalText}>
          💳 Paiements securises via Stripe (PCI-DSS){'\n'}
          📄 Facture TVA belge disponible{'\n'}
          ↩️ Droit de retractation 14 jours (Art. VI.47 CDE){'\n'}
          🔁 Renouvellement automatique — annulation a tout moment
        </Text>
      </View>

      <TouchableOpacity activeOpacity={0.75} style={styles.restoreBtn} onPress={handleRestore}>
        <Text style={styles.restoreBtnText}>Restaurer un abonnement existant</Text>
      </TouchableOpacity>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:  { flex: 1, backgroundColor: '#080B14' },
  content:    { padding: 16, paddingBottom: 40 },
  centerLoad: { flex: 1, justifyContent: 'center', alignItems: 'center' },

  hero: {
    borderRadius: 20,
    padding: 24,
    marginBottom: 14,
    alignItems: 'center',
    overflow: 'hidden',
  },
  heroEmoji: { fontSize: 36, marginBottom: 8 },
  heroTitle: { fontSize: 22, fontWeight: '900', color: '#FFF', marginBottom: 4, letterSpacing: 0.5 },
  heroSub:   { fontSize: 13, color: 'rgba(255,255,255,0.6)', textAlign: 'center' },
  heroEmail: { fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 6 },
  currentPlanBadge: {
    marginTop: 12,
    backgroundColor: 'rgba(196,90,45,0.25)',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: 'rgba(196,90,45,0.4)',
  },
  currentPlanText: { fontSize: 11, color: '#FFB84D', fontWeight: '700' },

  // Beta banner
  betaBanner: {
    backgroundColor: '#ECFDF5',
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#A7F3D0',
    alignItems: 'center',
  },
  betaTitle: { fontSize: 15, fontWeight: '800', color: '#065F46', marginBottom: 4 },
  betaText:  { fontSize: 12, color: '#047857', textAlign: 'center', lineHeight: 18 },

  // Toggle mensuel/annuel
  toggleContainer: {
    flexDirection: 'row',
    backgroundColor: '#0F1A2E',
    borderRadius: 14,
    padding: 4,
    marginBottom: 14,
  },
  togglePill: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 6,
  },
  togglePillActive: { backgroundColor: '#1A3A5C' },
  toggleText:       { fontSize: 13, fontWeight: '700', color: 'rgba(255,255,255,0.4)' },
  toggleTextActive: { color: '#FFF' },
  savePill: {
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  saveText: { fontSize: 10, fontWeight: '800', color: '#FFF' },

  quotaBar: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  quotaLabel: { fontSize: 12, color: colors.textSecondary, marginBottom: 6 },
  quotaTrack: { height: 6, backgroundColor: colors.border, borderRadius: 3, overflow: 'hidden' },
  quotaFill:  { height: '100%', borderRadius: 3 },

  errorBox: {
    backgroundColor: '#FEF2F2',
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#FCA5A5',
  },
  errorText: { fontSize: 12, color: colors.error },

  planCard: {
    backgroundColor: '#0F1629',
    borderRadius: 20,
    padding: 20,
    marginBottom: 14,
    elevation: 3,
    shadowColor: 'rgba(0,0,0,0.3)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 12,
    borderWidth: 1,
    borderColor: '#1E2A45',
  },
  planCardGradientBorder: {
    borderRadius: 20,
    padding: 2,
    marginBottom: 14,
    elevation: 4,
    shadowColor: 'rgba(108,63,160,0.3)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 16,
  },
  planCardInner: {
    backgroundColor: PRO_BG,
    borderRadius: 18,
    padding: 20,
  },
  planCardCurrent: { borderColor: GREEN, borderWidth: 2 },

  badge: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(0,0,0,0.06)',
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginBottom: 12,
  },
  badgeHighlight:     { backgroundColor: 'rgba(255,184,77,0.2)' },
  badgeText:          { fontSize: 10, fontWeight: '800', color: colors.textSecondary, letterSpacing: 0.5 },
  badgeTextHighlight: { color: '#FFB84D' },

  planHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 14 },
  planEmoji:  { fontSize: 28 },
  planInfo:   { flex: 1 },
  planName:   { fontSize: 17, fontWeight: '900', color: '#F0F4FF' },
  planNameHighlight:  { color: '#FFF' },
  planSubtitle: { fontSize: 11, color: colors.textMuted, marginTop: 2 },
  planPrice:          { fontSize: 28, fontWeight: '900', color: '#00D4AA', marginTop: 6 },
  planPriceHighlight: { color: '#FFF' },
  activePill:     { backgroundColor: '#D1FAE5', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 4 },
  activePillText: { fontSize: 10, fontWeight: '800', color: '#065F46' },

  // Founding member
  foundingBox: {
    backgroundColor: 'rgba(196,90,45,0.12)',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    marginBottom: 10,
  },
  foundingText: { fontSize: 11, color: ORANGE, fontWeight: '600' },

  featureList: { marginBottom: 14 },
  featureRow:  { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 8 },
  featureDot:   { width: 8, height: 8, borderRadius: 4 },
  featureDotOk: { backgroundColor: '#10B981' },
  featureDotNo: { backgroundColor: '#374151' },
  featureText:    { fontSize: 12, color: '#C8D6E5', flex: 1 },
  featureTextOff: { color: '#3A4A6A' },

  subscribeBtn:         { borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  subscribeBtnFallback: { backgroundColor: NAVY, borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  subscribeBtnText:     { color: '#FFF', fontSize: 15, fontWeight: '900', letterSpacing: 0.3 },

  cancelBtn:     { borderWidth: 1, borderColor: '#FCA5A5', borderRadius: 10, paddingVertical: 10, alignItems: 'center' },
  cancelBtnText: { fontSize: 12, color: colors.error, fontWeight: '600' },

  legalBox: {
    backgroundColor: '#F8FAFC',
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  legalText: { fontSize: 11, color: colors.textMuted, lineHeight: 18 },

  restoreBtn:     { alignItems: 'center', paddingVertical: 12 },
  restoreBtnText: { fontSize: 12, color: colors.primary, textDecorationLine: 'underline' },
});
