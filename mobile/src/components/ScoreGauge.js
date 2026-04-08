/**
 * ScoreGauge — Jauge de contestabilité animée
 * Props: score (0-100), level ('forte'|'moyenne'|'faible'), size
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

const COLORS = {
  forte:  { bar: '#10B981', bg: '#ECFDF5', text: '#065F46', label: 'Forte chance' },
  moyenne:{ bar: '#F59E0B', bg: '#FFFBEB', text: '#92400E', label: 'Contestable' },
  faible: { bar: '#EF4444', bg: '#FEF2F2', text: '#991B1B', label: 'Faible chance' },
};

export default function ScoreGauge({ score = 0, level = 'faible', compact = false }) {
  const c = COLORS[level] || COLORS.faible;
  const pct = Math.min(100, Math.max(0, score));

  if (compact) {
    return (
      <View style={[s.compactWrap, { backgroundColor: c.bg }]}>
        <Text style={[s.compactScore, { color: c.bar }]}>{pct}%</Text>
        <Text style={[s.compactLabel, { color: c.text }]}>{c.label}</Text>
      </View>
    );
  }

  return (
    <View style={[s.wrap, { backgroundColor: c.bg }]}>
      <View style={s.row}>
        <View style={s.left}>
          <Text style={[s.score, { color: c.bar }]}>{pct}%</Text>
          <Text style={[s.label, { color: c.text }]}>{c.label}</Text>
        </View>
        <Text style={s.icon}>
          {level === 'forte' ? '🟢' : level === 'moyenne' ? '🟠' : '🔴'}
        </Text>
      </View>
      <View style={s.barBg}>
        <View style={[s.barFill, { width: `${pct}%`, backgroundColor: c.bar }]} />
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { borderRadius: 14, padding: 16, marginBottom: 12 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  left: {},
  score: { fontSize: 32, fontWeight: '900' },
  label: { fontSize: 13, fontWeight: '700', marginTop: 2 },
  icon: { fontSize: 28 },
  barBg: { height: 8, backgroundColor: 'rgba(0,0,0,0.08)', borderRadius: 4, overflow: 'hidden' },
  barFill: { height: 8, borderRadius: 4 },
  // compact
  compactWrap: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20 },
  compactScore: { fontSize: 15, fontWeight: '900' },
  compactLabel: { fontSize: 11, fontWeight: '600' },
});
