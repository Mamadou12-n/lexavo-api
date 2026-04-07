/**
 * HistoryScreen — Lexavo
 * Liste les conversations de l'utilisateur depuis le backend /conversations.
 * Les messages d'une conversation sont chargés à la demande (au tap).
 */

import React, { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  Alert, StatusBar, ActivityIndicator,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getConversations, getConversationMessages } from '../api/client';
import { colors } from '../theme/colors';
import { LinearGradient } from 'expo-linear-gradient';

export default function HistoryScreen({ navigation }) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState(null);

  // Recharge la liste à chaque fois que l'écran redevient actif
  useFocusEffect(
    useCallback(() => {
      let active = true;
      setLoading(true);
      setError(null);

      getConversations()
        .then(({ conversations: list }) => {
          if (!active) return;
          // Tri décroissant par date de création
          const sorted = [...list].sort(
            (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          );
          setConversations(sorted);
        })
        .catch((err) => {
          if (!active) return;
          const msg =
            err.response?.data?.detail ||
            err.message ||
            'Impossible de charger l\'historique.';
          setError(msg);
        })
        .finally(() => {
          if (active) setLoading(false);
        });

      return () => { active = false; };
    }, [])
  );

  // Chargement des messages au tap, affichage en Alert
  const handlePress = useCallback(async (conversation) => {
    try {
      const { messages } = await getConversationMessages(conversation.id);
      if (!messages || messages.length === 0) {
        Alert.alert(conversation.title || 'Conversation', 'Aucun message dans cette conversation.');
        return;
      }
      const preview = messages
        .slice(0, 4)
        .map((m) => `${m.role === 'user' ? 'Q' : 'R'}: ${(m.content || '').slice(0, 100)}`)
        .join('\n\n');
      Alert.alert(
        conversation.title || 'Conversation',
        `${messages.length} message(s)\n\n${preview}${messages.length > 4 ? '\n\n…' : ''}`,
        [{ text: 'Fermer', style: 'cancel' }]
      );
    } catch (_) {
      Alert.alert('Erreur', 'Impossible de charger les messages.');
    }
  }, []);

  const formatDate = (dateStr) => {
    try {
      const d = new Date(dateStr);
      const now = new Date();
      const diffDays = Math.floor((now - d) / (1000 * 60 * 60 * 24));

      if (diffDays === 0) {
        return `Aujourd'hui, ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
      }
      if (diffDays === 1) return 'Hier';
      if (diffDays < 7) return `Il y a ${diffDays} jours`;

      return d.toLocaleDateString('fr-BE', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch (_) {
      return dateStr || '';
    }
  };

  const renderItem = useCallback(({ item }) => (
    <TouchableOpacity activeOpacity={0.75}
      style={styles.card}
      onPress={() => handlePress(item)}
      activeOpacity={0.85}
    >
      <View style={styles.cardHeader}>
        <View style={styles.cardIcon}>
          <Text style={styles.cardIconText}>&#x1F4AC;</Text>
        </View>
        <View style={styles.cardInfo}>
          <Text style={styles.cardTitle} numberOfLines={2}>
            {item.title || 'Sans titre'}
          </Text>
          <Text style={styles.cardDate}>{formatDate(item.created_at)}</Text>
        </View>
        <View style={styles.cardArrowWrap}>
          <Text style={styles.cardArrow}>&#x203A;</Text>
        </View>
      </View>
    </TouchableOpacity>
  ), [handlePress]);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.background} />

      {/* Header */}
      <LinearGradient colors={['#0A1628', '#1A3A5C']} style={styles.heroHeader}>
        <Text style={styles.heroEmoji}>📜</Text>
        <Text style={styles.heroTitle}>Historique</Text>
        <Text style={styles.heroSub}>
          {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
        </Text>
      </LinearGradient>

      {loading ? (
        <View style={styles.centerContent}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : error ? (
        <View style={styles.centerContent}>
          <Text style={styles.errorIcon}>&#x26A0;&#xFE0F;</Text>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity activeOpacity={0.75}
            style={styles.retryBtn}
            onPress={() => {
              setLoading(true);
              setError(null);
              getConversations()
                .then(({ conversations: list }) => {
                  const sorted = [...list].sort(
                    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
                  );
                  setConversations(sorted);
                })
                .catch((err) => setError(err.message || 'Erreur réseau.'))
                .finally(() => setLoading(false));
            }}
          >
            <Text style={styles.retryBtnText}>Réessayer</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={conversations}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>&#x1F4AD;</Text>
              <Text style={styles.emptyTitle}>Aucune conversation</Text>
              <Text style={styles.emptyText}>
                Vos conversations avec l'assistant juridique apparaîtront ici.
              </Text>
              <TouchableOpacity activeOpacity={0.75}
                style={styles.emptyBtn}
                onPress={() => navigation.navigate('Ask')}
                activeOpacity={0.8}
              >
                <Text style={styles.emptyBtnText}>Poser une question</Text>
              </TouchableOpacity>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },

  heroHeader: { borderRadius: 16, padding: 20, margin: 16, marginBottom: 0, alignItems: 'center' },
  heroEmoji: { fontSize: 32, marginBottom: 8 },
  heroTitle: { fontSize: 20, fontWeight: '900', color: '#FFF', letterSpacing: 0.5 },
  heroSub: { fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4, textAlign: 'center' },

  list: {
    padding: 16,
    paddingBottom: 40,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 16,
    marginBottom: 10,
    borderLeftWidth: 3,
    borderLeftColor: colors.primary,
    elevation: 2,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 1,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  cardIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  cardIconText: {
    fontSize: 18,
  },
  cardInfo: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.textPrimary,
    lineHeight: 20,
  },
  cardDate: {
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 2,
  },
  cardArrowWrap: {
    paddingLeft: 8,
  },
  cardArrow: {
    fontSize: 20,
    color: colors.textMuted,
  },

  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  errorIcon: {
    fontSize: 40,
    marginBottom: 12,
  },
  errorText: {
    fontSize: 14,
    color: colors.error,
    textAlign: 'center',
    marginBottom: 20,
    lineHeight: 20,
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
    fontWeight: '700',
  },

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
    marginBottom: 24,
  },
  emptyBtn: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingHorizontal: 24,
    paddingVertical: 12,
  },
  emptyBtnText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '700',
  },
});
