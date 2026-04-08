/**
 * ExtractedCard — Affiche les données extraites d'un PV/amende par OCR
 * Props: extracted{}, confidence(0-1), onEdit(field, value)
 */
import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from 'react-native';

const FIELDS = [
  { key: 'montant',           label: 'Montant (€)',        type: 'number' },
  { key: 'date_infraction',   label: 'Date infraction',    type: 'text' },
  { key: 'heure',             label: 'Heure',              type: 'text' },
  { key: 'lieu',              label: 'Lieu',               type: 'text' },
  { key: 'plaque',            label: 'Plaque',             type: 'text' },
  { key: 'code_infraction',   label: 'Code infraction',    type: 'text' },
  { key: 'vitesse_constatee', label: 'Vitesse constatée',  type: 'number' },
  { key: 'vitesse_autorisee', label: 'Vitesse autorisée',  type: 'number' },
  { key: 'organisme',         label: 'Organisme',          type: 'text' },
  { key: 'reference',         label: 'Référence PV',       type: 'text' },
  { key: 'date_notification', label: 'Date notification',  type: 'text' },
  { key: 'delai_contestation',label: 'Délai contestation', type: 'text' },
];

export default function ExtractedCard({ extracted = {}, confidence = 0.5, onEdit }) {
  const [editing, setEditing] = useState(null);
  const [editVal, setEditVal] = useState('');

  const pct = Math.round(confidence * 100);
  const confColor = pct >= 80 ? '#10B981' : pct >= 50 ? '#F59E0B' : '#EF4444';

  const startEdit = (key) => {
    setEditing(key);
    setEditVal(String(extracted[key] ?? ''));
  };

  const confirmEdit = (key) => {
    onEdit?.(key, editVal);
    setEditing(null);
  };

  const visibleFields = FIELDS.filter(f => extracted[f.key] !== null && extracted[f.key] !== undefined);

  return (
    <View style={s.wrap}>
      {/* Confidence badge */}
      <View style={s.confRow}>
        <Text style={s.confTitle}>Données extraites</Text>
        <View style={[s.confBadge, { backgroundColor: confColor + '20', borderColor: confColor }]}>
          <Text style={[s.confText, { color: confColor }]}>Confiance {pct}%</Text>
        </View>
      </View>

      <Text style={s.hint}>Touche un champ pour le corriger</Text>

      {visibleFields.map(f => (
        <TouchableOpacity key={f.key} style={s.row} onPress={() => startEdit(f.key)}>
          <Text style={s.fieldLabel}>{f.label}</Text>
          {editing === f.key ? (
            <View style={s.editRow}>
              <TextInput
                style={s.editInput}
                value={editVal}
                onChangeText={setEditVal}
                autoFocus
                keyboardType={f.type === 'number' ? 'numeric' : 'default'}
              />
              <TouchableOpacity onPress={() => confirmEdit(f.key)} style={s.okBtn}>
                <Text style={s.okText}>✓</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <Text style={s.fieldValue}>{String(extracted[f.key])} ✏️</Text>
          )}
        </TouchableOpacity>
      ))}

      {visibleFields.length === 0 && (
        <Text style={s.empty}>Aucune donnée extraite. Ajoutez les informations manuellement.</Text>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { backgroundColor: '#FFF', borderRadius: 14, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: '#E5E7EB' },
  confRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  confTitle: { fontSize: 14, fontWeight: '800', color: '#1F2937' },
  confBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, borderWidth: 1 },
  confText: { fontSize: 11, fontWeight: '700' },
  hint: { fontSize: 11, color: '#9CA3AF', marginBottom: 12 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8, borderTopWidth: 1, borderTopColor: '#F3F4F6' },
  fieldLabel: { fontSize: 12, color: '#6B7280', fontWeight: '600', flex: 1 },
  fieldValue: { fontSize: 13, color: '#1F2937', fontWeight: '700', flex: 1, textAlign: 'right' },
  editRow: { flex: 1, flexDirection: 'row', gap: 8, alignItems: 'center' },
  editInput: { flex: 1, borderBottomWidth: 2, borderBottomColor: '#C45A2D', fontSize: 13, color: '#1F2937', paddingVertical: 2 },
  okBtn: { width: 28, height: 28, backgroundColor: '#10B981', borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  okText: { color: '#FFF', fontSize: 14, fontWeight: '800' },
  empty: { color: '#9CA3AF', fontSize: 13, textAlign: 'center', padding: 12 },
});
