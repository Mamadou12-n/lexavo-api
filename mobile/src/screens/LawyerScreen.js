import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  ActivityIndicator, Modal, ScrollView, Linking, StatusBar,
} from 'react-native';
import { colors } from '../theme/colors';
import api from '../api/client';
import { LinearGradient } from 'expo-linear-gradient';

const SPECIALTIES = [
  { key: null, label: 'Toutes les specialites' },
  { key: 'droit_civil', label: 'Droit civil' },
  { key: 'droit_penal', label: 'Droit penal' },
  { key: 'droit_travail', label: 'Droit du travail' },
  { key: 'droit_famille', label: 'Droit de la famille' },
  { key: 'droit_commercial', label: 'Droit commercial' },
  { key: 'droit_fiscal', label: 'Droit fiscal' },
  { key: 'droit_immobilier', label: 'Droit immobilier' },
  { key: 'droit_administratif', label: 'Droit administratif' },
  { key: 'droit_social', label: 'Droit social' },
  { key: 'droit_europeen', label: 'Droit europeen' },
  { key: 'droit_rgpd', label: 'RGPD / Vie privee' },
];

export default function LawyerScreen() {
  const [lawyers, setLawyers] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSpecialty, setSelectedSpecialty] = useState(null);
  const [showFilter, setShowFilter] = useState(false);
  const [selectedLawyer, setSelectedLawyer] = useState(null);
  const [showProfile, setShowProfile] = useState(false);

  const fetchLawyers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/lawyers');
      const data = Array.isArray(response.data) ? response.data : (response.data?.lawyers || []);
      setLawyers(data);
      setFiltered(data);
    } catch (e) {
      setError(e.message || 'Impossible de charger la liste des avocats');
      setLawyers([]);
      setFiltered([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLawyers();
  }, [fetchLawyers]);

  useEffect(() => {
    if (!selectedSpecialty) {
      setFiltered(lawyers);
    } else {
      const result = lawyers.filter((l) => {
        const specs = l.specialties || l.specialites || [];
        return specs.some(
          (s) => s.toLowerCase().includes(selectedSpecialty.toLowerCase())
            || selectedSpecialty.toLowerCase().includes(s.toLowerCase())
        );
      });
      setFiltered(result);
    }
  }, [selectedSpecialty, lawyers]);

  const openProfile = useCallback((lawyer) => {
    setSelectedLawyer(lawyer);
    setShowProfile(true);
  }, []);

  const handleCall = useCallback((phone) => {
    if (phone) {
      Linking.openURL(`tel:${phone}`).catch(() => {});
    }
  }, []);

  const handleEmail = useCallback((email) => {
    if (email) {
      Linking.openURL(`mailto:${email}`).catch(() => {});
    }
  }, []);

  const renderSpecialtyBadge = (spec, index) => (
    <View key={`${spec}-${index}`} style={styles.specialtyBadge}>
      <Text style={styles.specialtyBadgeText}>{spec}</Text>
    </View>
  );

  const renderLawyerCard = useCallback(({ item }) => {
    const specialties = item.specialties || item.specialites || [];
    const rating = item.rating || item.note || 0;
    const fullStars = Math.min(Math.round(rating), 5);
    const emptyStars = 5 - fullStars;
    const starsText = '\u2605'.repeat(fullStars) + '\u2606'.repeat(emptyStars);

    return (
      <TouchableOpacity activeOpacity={0.75}
        style={styles.card}
        onPress={() => openProfile(item)}
        activeOpacity={0.85}
      >
        {/* Avatar */}
        <View style={styles.cardRow}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {(item.name || item.nom || '?').charAt(0).toUpperCase()}
            </Text>
          </View>
          <View style={styles.cardInfo}>
            <Text style={styles.cardName} numberOfLines={1}>
              {item.name || item.nom || 'Avocat'}
            </Text>
            <Text style={styles.cardBarreau} numberOfLines={1}>
              Barreau de {item.barreau || item.bar || '---'}
            </Text>
            <View style={styles.cardMeta}>
              {item.city || item.ville ? (
                <Text style={styles.cardCity}>
                  {item.city || item.ville}
                </Text>
              ) : null}
              {rating > 0 && (
                <Text style={styles.cardRating}>{starsText} {rating.toFixed(1)}</Text>
              )}
            </View>
          </View>
        </View>

        {/* Specialties */}
        {specialties.length > 0 && (
          <View style={styles.specialtiesRow}>
            {specialties.slice(0, 3).map((s, i) => renderSpecialtyBadge(s, i))}
            {specialties.length > 3 && (
              <View style={[styles.specialtyBadge, styles.specialtyBadgeMore]}>
                <Text style={styles.specialtyBadgeMoreText}>
                  +{specialties.length - 3}
                </Text>
              </View>
            )}
          </View>
        )}
      </TouchableOpacity>
    );
  }, [openProfile]);

  const currentFilterLabel = SPECIALTIES.find((s) => s.key === selectedSpecialty)?.label
    || 'Toutes les specialites';

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.background} />

      {/* Header */}
      <LinearGradient colors={['#0A1628', '#1A3A5C']} style={styles.heroHeader}>
        <Text style={styles.heroEmoji}>{'\uD83D\uDC68\u200D\u2696\uFE0F'}</Text>
        <Text style={styles.heroTitle}>Annuaire des avocats</Text>
        <Text style={styles.heroSub}>
          {filtered.length} avocat{filtered.length !== 1 ? 's' : ''}
        </Text>
      </LinearGradient>

      {/* Filter */}
      <TouchableOpacity activeOpacity={0.75}
        style={styles.filterBar}
        onPress={() => setShowFilter(true)}
        activeOpacity={0.8}
      >
        <Text style={styles.filterLabel}>Specialite :</Text>
        <Text style={styles.filterValue}>{currentFilterLabel}</Text>
        <Text style={styles.filterArrow}>{'\u25BC'}</Text>
      </TouchableOpacity>

      {/* Content */}
      {loading ? (
        <View style={styles.centerContent}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Chargement des avocats...</Text>
        </View>
      ) : error ? (
        <View style={styles.centerContent}>
          <Text style={styles.errorIcon}>{'\u26A0\uFE0F'}</Text>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={fetchLawyers} activeOpacity={0.8}>
            <Text style={styles.retryBtnText}>Reessayer</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(item, i) => String(item.id) || String(i)}
          renderItem={renderLawyerCard}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>{'\uD83D\uDD0D'}</Text>
              <Text style={styles.emptyTitle}>Aucun avocat trouve</Text>
              <Text style={styles.emptyText}>
                Essayez de modifier le filtre de specialite.
              </Text>
            </View>
          }
        />
      )}

      {/* Filter Modal */}
      <Modal
        visible={showFilter}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setShowFilter(false)}
      >
        <View style={styles.modal}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Filtrer par specialite</Text>
            <TouchableOpacity activeOpacity={0.75} onPress={() => setShowFilter(false)} style={styles.modalClose}>
              <Text style={styles.modalCloseText}>{'\u2715'}</Text>
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.modalContent}>
            {SPECIALTIES.map((spec) => (
              <TouchableOpacity activeOpacity={0.75}
                key={spec.key ?? 'all'}
                style={[
                  styles.filterOption,
                  selectedSpecialty === spec.key && styles.filterOptionActive,
                ]}
                onPress={() => {
                  setSelectedSpecialty(spec.key);
                  setShowFilter(false);
                }}
                activeOpacity={0.7}
              >
                <Text
                  style={[
                    styles.filterOptionText,
                    selectedSpecialty === spec.key && styles.filterOptionTextActive,
                  ]}
                >
                  {spec.label}
                </Text>
                {selectedSpecialty === spec.key && (
                  <Text style={styles.filterCheck}>{'\u2713'}</Text>
                )}
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      </Modal>

      {/* Profile Modal */}
      <Modal
        visible={showProfile}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setShowProfile(false)}
      >
        <LawyerProfile
          lawyer={selectedLawyer}
          onClose={() => setShowProfile(false)}
          onCall={handleCall}
          onEmail={handleEmail}
        />
      </Modal>
    </View>
  );
}

function LawyerProfile({ lawyer, onClose, onCall, onEmail }) {
  if (!lawyer) return null;

  const specialties = lawyer.specialties || lawyer.specialites || [];
  const rating = lawyer.rating || lawyer.note || 0;
  const fullStars = Math.min(Math.round(rating), 5);
  const emptyStars = 5 - fullStars;
  const starsText = '\u2605'.repeat(fullStars) + '\u2606'.repeat(emptyStars);

  return (
    <View style={styles.profileContainer}>
      <View style={styles.profileHeader}>
        <TouchableOpacity activeOpacity={0.75} onPress={onClose} style={styles.modalClose}>
          <Text style={styles.modalCloseText}>{'\u2715'}</Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.profileContent}>
        {/* Avatar + Name */}
        <View style={styles.profileTop}>
          <View style={styles.profileAvatar}>
            <Text style={styles.profileAvatarText}>
              {(lawyer.name || lawyer.nom || '?').charAt(0).toUpperCase()}
            </Text>
          </View>
          <Text style={styles.profileName}>
            {lawyer.name || lawyer.nom || 'Avocat'}
          </Text>
          <Text style={styles.profileBarreau}>
            Barreau de {lawyer.barreau || lawyer.bar || '---'}
          </Text>
          {rating > 0 && (
            <View style={styles.profileRatingRow}>
              <Text style={styles.profileStars}>{starsText}</Text>
              <Text style={styles.profileRatingValue}>{rating.toFixed(1)}/5</Text>
            </View>
          )}
        </View>

        {/* Info */}
        {(lawyer.city || lawyer.ville) && (
          <InfoRow label="Ville" value={lawyer.city || lawyer.ville} />
        )}
        {(lawyer.address || lawyer.adresse) && (
          <InfoRow label="Adresse" value={lawyer.address || lawyer.adresse} />
        )}
        {(lawyer.phone || lawyer.telephone) && (
          <InfoRow label="Telephone" value={lawyer.phone || lawyer.telephone} />
        )}
        {lawyer.email && (
          <InfoRow label="Email" value={lawyer.email} />
        )}
        {(lawyer.languages || lawyer.langues) && (
          <InfoRow
            label="Langues"
            value={(lawyer.languages || lawyer.langues || []).join(', ')}
          />
        )}

        {/* Specialties */}
        {specialties.length > 0 && (
          <View style={styles.profileSection}>
            <Text style={styles.profileSectionTitle}>Specialites</Text>
            <View style={styles.profileSpecialties}>
              {specialties.map((s, i) => (
                <View key={`${s}-${i}`} style={styles.profileSpecBadge}>
                  <Text style={styles.profileSpecText}>{s}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Contact buttons */}
        <View style={styles.contactBtns}>
          {(lawyer.phone || lawyer.telephone) && (
            <TouchableOpacity activeOpacity={0.75}
              style={styles.contactBtn}
              onPress={() => onCall(lawyer.phone || lawyer.telephone)}
              activeOpacity={0.8}
            >
              <Text style={styles.contactBtnIcon}>{'\uD83D\uDCDE'}</Text>
              <Text style={styles.contactBtnText}>Appeler</Text>
            </TouchableOpacity>
          )}
          {lawyer.email && (
            <TouchableOpacity activeOpacity={0.75}
              style={[styles.contactBtn, styles.contactBtnEmail]}
              onPress={() => onEmail(lawyer.email)}
              activeOpacity={0.8}
            >
              <Text style={styles.contactBtnIcon}>{'\u2709\uFE0F'}</Text>
              <Text style={[styles.contactBtnText, styles.contactBtnEmailText]}>
                Envoyer un email
              </Text>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>
    </View>
  );
}

function InfoRow({ label, value }) {
  return (
    <View style={styles.profileInfoRow}>
      <Text style={styles.profileInfoLabel}>{label}</Text>
      <Text style={styles.profileInfoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },

  // Header
  heroHeader: { borderRadius: 16, padding: 20, margin: 16, marginBottom: 0, alignItems: 'center' },
  heroEmoji: { fontSize: 32, marginBottom: 8 },
  heroTitle: { fontSize: 20, fontWeight: '900', color: '#FFF', letterSpacing: 0.5 },
  heroSub: { fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4, textAlign: 'center' },

  // Filter bar
  filterBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  filterLabel: {
    fontSize: 12,
    color: colors.textMuted,
    marginRight: 6,
  },
  filterValue: {
    flex: 1,
    fontSize: 13,
    fontWeight: '600',
    color: colors.primary,
  },
  filterArrow: {
    fontSize: 10,
    color: colors.textMuted,
  },

  // Content states
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  loadingText: {
    fontSize: 13,
    color: colors.textMuted,
    marginTop: 12,
  },
  errorIcon: {
    fontSize: 40,
    marginBottom: 12,
  },
  errorText: {
    fontSize: 14,
    color: colors.error,
    textAlign: 'center',
    marginBottom: 16,
  },
  retryBtn: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingHorizontal: 24,
    paddingVertical: 10,
  },
  retryBtnText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
  },

  // List
  list: {
    padding: 16,
    paddingBottom: 40,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 16,
    marginBottom: 10,
    elevation: 2,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 1,
    borderLeftWidth: 3,
    borderLeftColor: colors.accent,
  },
  cardRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  avatarText: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: '700',
  },
  cardInfo: {
    flex: 1,
  },
  cardName: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  cardBarreau: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 1,
  },
  cardMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 3,
    gap: 10,
  },
  cardCity: {
    fontSize: 11,
    color: colors.textMuted,
  },
  cardRating: {
    fontSize: 11,
    color: colors.accent,
    fontWeight: '600',
  },
  specialtiesRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 10,
    gap: 6,
  },
  specialtyBadge: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderWidth: 1,
    borderColor: colors.border,
  },
  specialtyBadgeText: {
    fontSize: 11,
    color: colors.textSecondary,
    fontWeight: '500',
  },
  specialtyBadgeMore: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  specialtyBadgeMoreText: {
    fontSize: 11,
    color: '#FFF',
    fontWeight: '600',
  },

  // Empty
  emptyState: {
    alignItems: 'center',
    paddingTop: 80,
    paddingHorizontal: 40,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
  },

  // Filter Modal
  modal: {
    flex: 1,
    backgroundColor: colors.background,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  modalTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  modalClose: {
    padding: 6,
  },
  modalCloseText: {
    fontSize: 18,
    color: colors.textSecondary,
  },
  modalContent: {
    padding: 16,
  },
  filterOption: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 10,
    padding: 14,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: colors.border,
  },
  filterOptionActive: {
    borderColor: colors.primary,
    backgroundColor: '#EEF3FA',
  },
  filterOptionText: {
    fontSize: 14,
    color: colors.textPrimary,
  },
  filterOptionTextActive: {
    color: colors.primary,
    fontWeight: '700',
  },
  filterCheck: {
    fontSize: 16,
    color: colors.primary,
    fontWeight: '700',
  },

  // Profile
  profileContainer: {
    flex: 1,
    backgroundColor: colors.background,
  },
  profileHeader: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    padding: 16,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  profileContent: {
    padding: 20,
    paddingBottom: 40,
  },
  profileTop: {
    alignItems: 'center',
    marginBottom: 24,
  },
  profileAvatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  profileAvatarText: {
    color: '#FFF',
    fontSize: 28,
    fontWeight: '700',
  },
  profileName: {
    fontSize: 20,
    fontWeight: '800',
    color: colors.textPrimary,
    textAlign: 'center',
  },
  profileBarreau: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 4,
  },
  profileRatingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    gap: 6,
  },
  profileStars: {
    fontSize: 16,
    color: colors.accent,
  },
  profileRatingValue: {
    fontSize: 13,
    color: colors.textSecondary,
    fontWeight: '600',
  },

  // Profile info rows
  profileInfoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: colors.surface,
    borderRadius: 10,
    padding: 12,
    marginBottom: 6,
  },
  profileInfoLabel: {
    fontSize: 12,
    color: colors.textMuted,
    textTransform: 'uppercase',
  },
  profileInfoValue: {
    fontSize: 13,
    color: colors.textPrimary,
    fontWeight: '600',
    flex: 1,
    textAlign: 'right',
    marginLeft: 12,
  },

  // Profile specialties
  profileSection: {
    marginTop: 16,
  },
  profileSectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: 10,
  },
  profileSpecialties: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  profileSpecBadge: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  profileSpecText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '600',
  },

  // Contact buttons
  contactBtns: {
    marginTop: 24,
    gap: 10,
  },
  contactBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.success,
    borderRadius: 14,
    paddingVertical: 14,
    gap: 8,
  },
  contactBtnEmail: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: colors.primary,
  },
  contactBtnIcon: {
    fontSize: 18,
  },
  contactBtnText: {
    color: '#FFF',
    fontSize: 15,
    fontWeight: '700',
  },
  contactBtnEmailText: {
    color: colors.primary,
  },
});
