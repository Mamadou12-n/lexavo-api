import React, { useState, useRef } from 'react';
import {
  View, Text, TouchableOpacity, ActivityIndicator,
  StyleSheet, SafeAreaView, Platform,
} from 'react-native';
import { WebView } from 'react-native-webview';
import { colors } from '../../theme/designSystem';

const NLM_URL = 'https://notebooklm.google.com';

export default function NotebookLMScreen({ onBack }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const webRef = useRef(null);

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={onBack} style={s.backBtn} accessibilityRole="button" accessibilityLabel="Retour">
          <Text style={s.backText}>← Retour</Text>
        </TouchableOpacity>
        <Text style={s.title}>NotebookLM</Text>
        <View style={s.backBtn} />
      </View>

      {loading && (
        <View style={s.loaderRow}>
          <ActivityIndicator color={colors.brand} size="small" />
          <Text style={s.loaderText}>Chargement NotebookLM...</Text>
        </View>
      )}

      {error ? (
        <View style={s.errorBox}>
          <Text style={s.errorText}>Impossible de charger NotebookLM.</Text>
          <TouchableOpacity
            style={s.retryBtn}
            onPress={() => { setError(false); setLoading(true); webRef.current?.reload(); }}
            accessibilityRole="button"
          >
            <Text style={s.retryText}>Réessayer</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <WebView
          ref={webRef}
          source={{ uri: NLM_URL }}
          style={s.webview}
          javaScriptEnabled
          domStorageEnabled
          thirdPartyCookiesEnabled
          allowsInlineMediaPlayback
          mediaPlaybackRequiresUserAction={false}
          onLoadStart={() => setLoading(true)}
          onLoadEnd={() => setLoading(false)}
          onError={() => { setLoading(false); setError(true); }}
          userAgent={
            Platform.OS === 'android'
              ? 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36'
              : 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1'
          }
        />
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 16, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },
  backBtn: { width: 80 },
  backText: { color: colors.brand, fontSize: 15, fontWeight: '600' },
  title: { fontSize: 16, fontWeight: '700', color: colors.textPrimary },
  webview: { flex: 1 },
  loaderRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    paddingVertical: 8, gap: 8, backgroundColor: colors.surface,
  },
  loaderText: { fontSize: 13, color: colors.textSecondary },
  errorBox: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16, padding: 32 },
  errorText: { fontSize: 15, color: colors.textSecondary, textAlign: 'center' },
  retryBtn: {
    backgroundColor: colors.brand, paddingHorizontal: 24, paddingVertical: 12, borderRadius: 8,
  },
  retryText: { color: '#fff', fontWeight: '600', fontSize: 14 },
});
