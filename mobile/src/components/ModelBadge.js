import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

const MODEL_MAP = {
  haiku:  { icon: '⚡', label: 'Haiku',  desc: 'Réponse rapide',  color: '#27AE60', bg: '#F0FDF4', border: '#BBF7D0' },
  sonnet: { icon: '🔵', label: 'Sonnet', desc: 'Analyse avancée', color: '#2980B9', bg: '#EBF5FB', border: '#BFDBFE' },
  opus:   { icon: '💎', label: 'Opus',   desc: 'Cas complexe',    color: '#D4A017', bg: '#FFFBEB', border: '#FDE68A' },
};

function detectModel(modelStr) {
  if (!modelStr) return null;
  const s = modelStr.toLowerCase();
  if (s.includes('haiku'))  return 'haiku';
  if (s.includes('sonnet')) return 'sonnet';
  if (s.includes('opus'))   return 'opus';
  return null;
}

export default function ModelBadge({ model, style }) {
  const key = detectModel(model);
  if (!key) return null;
  const m = MODEL_MAP[key];
  return (
    <View style={[styles.badge, { backgroundColor: m.bg, borderColor: m.border }, style]}>
      <Text style={styles.icon}>{m.icon}</Text>
      <Text style={[styles.label, { color: m.color }]}>{m.label}</Text>
      <Text style={styles.sep}>·</Text>
      <Text style={[styles.desc, { color: m.color }]}>{m.desc}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
    alignSelf: 'flex-end',
    marginBottom: 10,
  },
  icon:  { fontSize: 10 },
  label: { fontSize: 10, fontWeight: '700' },
  sep:   { fontSize: 9, color: '#CBD5E1' },
  desc:  { fontSize: 9, fontWeight: '500' },
});
