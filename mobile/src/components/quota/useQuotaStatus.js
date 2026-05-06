/**
 * useQuotaStatus — Hook React pour le paywall progressif.
 *
 * - Fetch /billing/quota/status au mount
 * - Refresh manuel via refresh()
 * - Détecte le warning_level pour piloter banner + modals
 * - Tracking session pour ne pas re-afficher le warning à 80% en boucle
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getQuotaStatus } from '../../api/client';

const SESSION_FLAG_KEY = '@lexavo_quota_warn_shown_session';

export default function useQuotaStatus({ autoFetch = true } = {}) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(autoFetch);
  const [error, setError] = useState(null);
  const [showWarningModal, setShowWarningModal] = useState(false);
  const [showBlockedModal, setShowBlockedModal] = useState(false);
  const warnedThisSessionRef = useRef(false);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getQuotaStatus();
      setStatus(data);
      return data;
    } catch (e) {
      setError(e?.message || 'fetch_error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (autoFetch) fetchStatus();
  }, [autoFetch, fetchStatus]);

  // Décide s'il faut afficher le warning modal (1x par session)
  const maybeShowWarning = useCallback(async (currentStatus) => {
    if (!currentStatus) return;
    if (currentStatus.warning_level !== 'hard') return;
    if (warnedThisSessionRef.current) return;
    try {
      const flag = await AsyncStorage.getItem(SESSION_FLAG_KEY);
      if (flag === '1') return;
      await AsyncStorage.setItem(SESSION_FLAG_KEY, '1');
    } catch {
      // ignore — affiche quand même
    }
    warnedThisSessionRef.current = true;
    setShowWarningModal(true);
  }, []);

  // Reset le flag de session (à appeler au logout / login)
  const resetSessionWarning = useCallback(async () => {
    warnedThisSessionRef.current = false;
    try {
      await AsyncStorage.removeItem(SESSION_FLAG_KEY);
    } catch {}
  }, []);

  // Trigger blocked modal automatiquement si quota épuisé
  useEffect(() => {
    if (status?.warning_level === 'blocked') {
      setShowBlockedModal(true);
    }
    if (status?.warning_level === 'hard') {
      maybeShowWarning(status);
    }
  }, [status, maybeShowWarning]);

  return {
    status,
    loading,
    error,
    refresh: fetchStatus,
    showWarningModal,
    setShowWarningModal,
    showBlockedModal,
    setShowBlockedModal,
    resetSessionWarning,
    isBlocked: status?.warning_level === 'blocked',
  };
}
