/**
 * Paywall progressif — exports publics.
 *
 * Usage typique dans un screen :
 *   import { QuotaBanner, QuotaWarningModal, QuotaBlockedModal, useQuotaStatus } from '../components/quota';
 *
 *   const navigation = useNavigation();
 *   const goSubscription = () => navigation.navigate('Subscription');
 *   const q = useQuotaStatus();
 *
 *   <QuotaBanner status={q.status} onPress={goSubscription} />
 *   <QuotaWarningModal visible={q.showWarningModal} status={q.status}
 *     onUpgrade={() => { q.setShowWarningModal(false); goSubscription(); }}
 *     onDismiss={() => q.setShowWarningModal(false)} />
 *   <QuotaBlockedModal visible={q.showBlockedModal} status={q.status}
 *     onUpgrade={() => { q.setShowBlockedModal(false); goSubscription(); }}
 *     onClose={() => q.setShowBlockedModal(false)} />
 */
export { default as QuotaBanner } from './QuotaBanner';
export { default as QuotaWarningModal } from './QuotaWarningModal';
export { default as QuotaBlockedModal } from './QuotaBlockedModal';
export { default as useQuotaStatus } from './useQuotaStatus';
