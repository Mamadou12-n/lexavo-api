import React, { useState, useCallback } from 'react';
import {
  View, Text, TextInput, StyleSheet, FlatList, TouchableOpacity,
  ActivityIndicator, Modal, ScrollView, KeyboardAvoidingView, Platform,
} from 'react-native';
import { searchDocuments, SOURCES } from '../api/client';
import { colors } from '../theme/colors';
import ResultCard from '../components/ResultCard';
import SourceBadge from '../components/SourceBadge';

export default function SearchScreen({ navigation }) {
  const [query, setQuery]           = useState('');
  const [results, setResults]       = useState([]);
  const [total, setTotal]           = useState(0);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);
  const [sourceFilter, setSourceFilter] = useState(null);
  const [topK, setTopK]             = useState(10);
  const [selectedDoc, setSelectedDoc]   = useState(null);
  const [showModal, setShowModal]       = useState(false);

  const search = useCallback(async (q = query) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    setError(null);
    setLoading(true);
    setResults([]);

    try {
      const data = await searchDocuments(trimmed, {
        top_k: topK,
        source_filter: sourceFilter,
      });
      setResults(data.results ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      if (e.response?.status === 503) {
        setError('Index indisponible.\nLancez : python run_all.py --phase indexing');
      } else {
        setError(e.message || 'Erreur réseau');
      }
    } finally {
      setLoading(false);
    }
  }, [query, topK, sourceFilter]);

  const openDoc = (item) => {
    setSelectedDoc(item);
    setShowModal(true);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      {/* Barre de recherche */}
      <View style={styles.searchBar}>
        <TextInput
          style={styles.input}
          placeholder="Rechercher dans la base juridique..."
          placeholderTextColor={colors.textMuted}
          value={query}
          onChangeText={setQuery}
          onSubmitEditing={() => search()}
          returnKeyType="search"
        />
        <TouchableOpacity activeOpacity={0.75}
          style={[styles.searchBtn, (!query.trim() || loading) && styles.searchBtnDisabled]}
          onPress={() => search()}
          disabled={!query.trim() || loading}
        >
          {loading ? (
            <ActivityIndicator color="#FFF" size="small" />
          ) : (
            <Text style={styles.searchBtnText}>🔍</Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Filtres rapides (sources) */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.filtersRow}
        contentContainerStyle={styles.filtersContent}
      >
        {SOURCES.map((s) => (
          <TouchableOpacity activeOpacity={0.75}
            key={s.key ?? 'all'}
            style={[styles.chip, sourceFilter === s.key && styles.chipActive]}
            onPress={() => setSourceFilter(s.key)}
          >
            <Text style={[styles.chipText, sourceFilter === s.key && styles.chipTextActive]}>
              {s.emoji} {s.key ?? 'Tout'}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Nb résultats */}
      {total > 0 && !loading && (
        <View style={styles.resultsHeader}>
          <Text style={styles.resultsCount}>
            {total} résultat{total > 1 ? 's' : ''}
            {sourceFilter ? ` · ${sourceFilter}` : ''}
          </Text>
          <TouchableOpacity activeOpacity={0.75} onPress={() => setTopK(topK === 10 ? 20 : 10)}>
            <Text style={styles.topKToggle}>Top {topK} ▼</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Erreur */}
      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>⚠️ {error}</Text>
        </View>
      )}

      {/* Résultats */}
      <FlatList
        data={results}
        keyExtractor={(item, i) => item.doc_id || String(i)}
        renderItem={({ item }) => (
          <ResultCard item={item} onPress={() => openDoc(item)} />
        )}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !loading && query ? (
            <View style={styles.empty}>
              <Text style={styles.emptyIcon}>🔍</Text>
              <Text style={styles.emptyText}>Aucun résultat pour "{query}"</Text>
            </View>
          ) : null
        }
      />

      {/* Modal détail document */}
      <Modal
        visible={showModal}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setShowModal(false)}
      >
        <DocumentDetail doc={selectedDoc} onClose={() => setShowModal(false)} />
      </Modal>
    </KeyboardAvoidingView>
  );
}

function DocumentDetail({ doc, onClose }) {
  if (!doc) return null;
  return (
    <View style={styles.modal}>
      {/* Header */}
      <View style={styles.modalHeader}>
        <SourceBadge source={doc.source || ''} />
        <TouchableOpacity activeOpacity={0.75} onPress={onClose} style={styles.closeBtn}>
          <Text style={styles.closeBtnText}>✕</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.modalScroll} contentContainerStyle={styles.modalContent}>
        {/* Titre */}
        {doc.title ? (
          <Text style={styles.modalTitle}>{doc.title}</Text>
        ) : null}

        {/* Métadonnées */}
        <View style={styles.metaRow}>
          {doc.date ? <MetaItem label="Date" value={doc.date.slice(0, 10)} /> : null}
          {doc.ecli ? <MetaItem label="ECLI" value={doc.ecli} mono /> : null}
          {doc.jurisdiction ? <MetaItem label="Juridiction" value={doc.jurisdiction} /> : null}
        </View>

        {/* Score */}
        {doc.similarity != null && (
          <View style={styles.scoreRow}>
            <Text style={styles.scoreLabel}>Pertinence vectorielle</Text>
            <View style={styles.scoreBar}>
              <View style={[styles.scoreFill, { width: `${doc.similarity * 100}%` }]} />
            </View>
            <Text style={styles.scoreValue}>{(doc.similarity * 100).toFixed(1)}%</Text>
          </View>
        )}

        {/* Extrait */}
        {doc.chunk_text && (
          <View style={styles.chunkBox}>
            <Text style={styles.chunkLabel}>Extrait pertinent</Text>
            <Text style={styles.chunkText}>{doc.chunk_text}</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

function MetaItem({ label, value, mono = false }) {
  return (
    <View style={styles.metaItem}>
      <Text style={styles.metaLabel}>{label}</Text>
      <Text style={[styles.metaValue, mono && { fontFamily: 'monospace', fontSize: 10 }]}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },

  searchBar: {
    flexDirection: 'row',
    padding: 12,
    paddingBottom: 8,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    gap: 8,
  },
  input: {
    flex: 1,
    backgroundColor: colors.background,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 14,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.border,
  },
  searchBtn: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    width: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  searchBtnDisabled: { opacity: 0.5 },
  searchBtnText: { fontSize: 18 },

  filtersRow:    { maxHeight: 44, backgroundColor: colors.surface },
  filtersContent: { paddingHorizontal: 12, paddingVertical: 8, gap: 6 },
  chip: {
    paddingHorizontal: 12, paddingVertical: 5,
    borderRadius: 16, borderWidth: 1, borderColor: colors.border,
    backgroundColor: colors.background,
  },
  chipActive:     { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText:       { fontSize: 11, color: colors.textSecondary },
  chipTextActive: { color: '#FFF', fontWeight: '600' },

  resultsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  resultsCount: { fontSize: 12, color: colors.textMuted },
  topKToggle:   { fontSize: 12, color: colors.primaryLight, fontWeight: '600' },

  errorBox: {
    margin: 12,
    backgroundColor: '#FEF2F2',
    borderRadius: 8,
    padding: 12,
  },
  errorText: { fontSize: 13, color: colors.error, fontFamily: 'monospace' },

  list: { padding: 12 },
  empty: { alignItems: 'center', marginTop: 60 },
  emptyIcon: { fontSize: 40, marginBottom: 12 },
  emptyText: { fontSize: 14, color: colors.textMuted, textAlign: 'center' },

  // Modal détail
  modal:       { flex: 1, backgroundColor: colors.background },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },
  closeBtn:     { padding: 6 },
  closeBtnText: { fontSize: 18, color: colors.textSecondary },
  modalScroll:  { flex: 1 },
  modalContent: { padding: 16, paddingBottom: 40 },
  modalTitle:   { fontSize: 18, fontWeight: '700', color: colors.textPrimary, lineHeight: 26, marginBottom: 12 },

  metaRow:   { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 },
  metaItem:  { backgroundColor: colors.surface, borderRadius: 8, padding: 8, minWidth: 100, flex: 1 },
  metaLabel: { fontSize: 10, color: colors.textMuted, textTransform: 'uppercase', marginBottom: 2 },
  metaValue: { fontSize: 12, color: colors.textPrimary, fontWeight: '600' },

  scoreRow:  { marginBottom: 16 },
  scoreLabel: { fontSize: 11, color: colors.textMuted, marginBottom: 4 },
  scoreBar:  {
    height: 6, backgroundColor: colors.border,
    borderRadius: 3, overflow: 'hidden', marginBottom: 2,
  },
  scoreFill: { height: '100%', backgroundColor: colors.primary, borderRadius: 3 },
  scoreValue: { fontSize: 11, color: colors.primary, fontWeight: '700', textAlign: 'right' },

  chunkBox: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 10,
    padding: 14,
    borderLeftWidth: 3,
    borderLeftColor: colors.primary,
  },
  chunkLabel: { fontSize: 11, fontWeight: '700', color: colors.textSecondary, marginBottom: 6, textTransform: 'uppercase' },
  chunkText:  { fontSize: 13, color: colors.textPrimary, lineHeight: 20 },
});
