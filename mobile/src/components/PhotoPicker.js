/**
 * PhotoPicker — Composant réutilisable pour ajouter des photos
 * Utilisé dans tous les outils Lexavo (Defend, Shield, Decode, etc.)
 * Permet de prendre une photo ou d'en choisir une depuis la galerie.
 */

import React, { useState } from 'react';
import { View, Text, TouchableOpacity, Image, StyleSheet, Alert, ScrollView } from 'react-native';
import * as ImagePicker from 'expo-image-picker';

const LEXAVO_ORANGE = '#C45A2D';

export default function PhotoPicker({ photos = [], onPhotosChange = () => {}, maxPhotos = 3, label = '📷 Ajouter une photo' }) {
  const pickImage = async (useCamera) => {
    if (photos.length >= maxPhotos) {
      Alert.alert('Maximum atteint', `Vous pouvez ajouter maximum ${maxPhotos} photos.`);
      return;
    }

    let permission;
    if (useCamera) {
      permission = await ImagePicker.requestCameraPermissionsAsync();
    } else {
      permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    }

    if (!permission.granted) {
      Alert.alert('Permission requise', 'Autorisez l\'accès pour ajouter des photos.');
      return;
    }

    const options = {
      mediaTypes: ['images'],
      allowsEditing: false,
      quality: 0.7,
      base64: true,
    };

    let result;
    if (useCamera) {
      result = await ImagePicker.launchCameraAsync(options);
    } else {
      result = await ImagePicker.launchImageLibraryAsync(options);
    }

    if (!result.canceled && result.assets?.[0]) {
      const asset = result.assets[0];
      onPhotosChange([...photos, { uri: asset.uri, base64: asset.base64 }]);
    }
  };

  const showOptions = () => {
    Alert.alert('Ajouter une photo', 'Choisissez une source', [
      { text: '📷 Appareil photo', onPress: () => pickImage(true) },
      { text: '🖼️ Galerie', onPress: () => pickImage(false) },
      { text: 'Annuler', style: 'cancel' },
    ]);
  };

  const removePhoto = (index) => {
    const updated = photos.filter((_, i) => i !== index);
    onPhotosChange(updated);
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity style={styles.addBtn} onPress={showOptions} activeOpacity={0.75}>
        <Text style={styles.addBtnText}>{label}</Text>
        <Text style={styles.addBtnCount}>{photos.length}/{maxPhotos}</Text>
      </TouchableOpacity>

      {photos.length > 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.photoRow}>
          {photos.map((photo, i) => (
            <View key={i} style={styles.photoWrapper}>
              <Image source={{ uri: photo.uri }} style={styles.photoThumb} />
              <TouchableOpacity activeOpacity={0.75} style={styles.removeBtn} onPress={() => removePhoto(i)}>
                <Text style={styles.removeBtnText}>✕</Text>
              </TouchableOpacity>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginBottom: 12 },
  addBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#FFF7ED',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#FDBA74',
    borderStyle: 'dashed',
  },
  addBtnText: { fontSize: 13, fontWeight: '600', color: LEXAVO_ORANGE },
  addBtnCount: { fontSize: 11, color: '#94A3B8' },
  photoRow: { marginTop: 8 },
  photoWrapper: { position: 'relative', marginRight: 8 },
  photoThumb: { width: 72, height: 72, borderRadius: 8 },
  removeBtn: {
    position: 'absolute', top: -6, right: -6,
    backgroundColor: '#EF4444', borderRadius: 10,
    width: 20, height: 20, alignItems: 'center', justifyContent: 'center',
  },
  removeBtnText: { color: '#FFF', fontSize: 10, fontWeight: '700' },
});
