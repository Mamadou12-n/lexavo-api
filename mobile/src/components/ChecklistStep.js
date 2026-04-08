/**
 * ChecklistStep — Questionnaire guidé de vices de forme
 * Props: questions[], answers{}, onAnswer(id, bool), score(0-100), level
 */
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import ScoreGauge from './ScoreGauge';

export default function ChecklistStep({ questions = [], answers = {}, onAnswer, score = 0, level = 'faible' }) {
  const answered = Object.keys(answers).length;

  return (
    <View>
      {/* Score en temps réel */}
      <ScoreGauge score={score} level={level} />

      <Text style={s.progress}>{answered}/{questions.length} questions répondues</Text>

      {questions.map((q, i) => {
        const val = answers[q.id];
        return (
          <View key={q.id} style={s.card}>
            <View style={s.numRow}>
              <View style={s.numCircle}><Text style={s.num}>{i + 1}</Text></View>
              <Text style={s.question}>{q.question}</Text>
            </View>
            <View style={s.btnRow}>
              <TouchableOpacity
                style={[s.btn, val === true && s.btnOui]}
                onPress={() => onAnswer(q.id, true)}
              >
                <Text style={[s.btnText, val === true && s.btnTextActive]}>✓ Oui</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[s.btn, val === false && s.btnNon]}
                onPress={() => onAnswer(q.id, false)}
              >
                <Text style={[s.btnText, val === false && s.btnTextActive]}>✗ Non</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[s.btn, val === null && s.btnNsp]}
                onPress={() => onAnswer(q.id, null)}
              >
                <Text style={[s.btnText, val === null && { color: '#6B7280', fontWeight: '700' }]}>— NSP</Text>
              </TouchableOpacity>
            </View>
            {/* Indice si réponse favorable */}
            {val !== undefined && q.vice && (
              <Text style={s.hint}>💡 {q.vice}</Text>
            )}
          </View>
        );
      })}
    </View>
  );
}

const s = StyleSheet.create({
  progress: { fontSize: 12, color: '#6B7280', fontWeight: '600', marginBottom: 12, textAlign: 'center' },
  card: {
    backgroundColor: '#FFF', borderRadius: 12, padding: 14, marginBottom: 10,
    borderWidth: 1, borderColor: '#E5E7EB',
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, elevation: 2,
  },
  numRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 12 },
  numCircle: { width: 24, height: 24, borderRadius: 12, backgroundColor: '#C45A2D', alignItems: 'center', justifyContent: 'center', marginTop: 1 },
  num: { color: '#FFF', fontSize: 11, fontWeight: '800' },
  question: { flex: 1, fontSize: 13, color: '#1F2937', lineHeight: 19, fontWeight: '500' },
  btnRow: { flexDirection: 'row', gap: 8 },
  btn: {
    flex: 1, paddingVertical: 9, borderRadius: 10, borderWidth: 1.5,
    borderColor: '#D1D5DB', backgroundColor: '#F9FAFB', alignItems: 'center',
  },
  btnOui: { borderColor: '#10B981', backgroundColor: '#ECFDF5' },
  btnNon: { borderColor: '#EF4444', backgroundColor: '#FEF2F2' },
  btnNsp: { borderColor: '#9CA3AF', backgroundColor: '#F3F4F6' },
  btnText: { fontSize: 12, fontWeight: '600', color: '#6B7280' },
  btnTextActive: { fontWeight: '800' },
  hint: { fontSize: 11, color: '#6B7280', fontStyle: 'italic', marginTop: 8, lineHeight: 16 },
});
