import { useState, useCallback } from 'react';
import { Alert } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import {
  getSharedNotes,
  getSharedNote,
  shareNote,
  uploadStudentDoc,
} from '../../../api/client';

export function useSharedNotes() {
  const [notesModal, setNotesModal] = useState(false);
  const [notesTab, setNotesTab] = useState('browse');
  const [notesList, setNotesList] = useState([]);
  const [activeNote, setActiveNote] = useState(null);
  const [notesLoading, setNotesLoading] = useState(false);
  const [notesSubjectFilter, setNotesSubjectFilter] = useState(null);
  const [shareForm, setShareForm] = useState({
    title: '', subject: 'droit_civil', content: '',
    university: '', year: '', anonymous: true, authorName: '',
  });
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadedDoc, setUploadedDoc] = useState({ text: '', filename: '' });

  const loadNotes = useCallback(async (subject = null) => {
    setNotesLoading(true);
    try {
      const data = await getSharedNotes(subject);
      setNotesList(data?.notes || []);
    } catch (_) {}
    finally { setNotesLoading(false); }
  }, []);

  const openNote = useCallback(async (noteId) => {
    try {
      const n = await getSharedNote(noteId);
      setActiveNote(n);
      setNotesTab('view');
    } catch (_) {}
  }, []);

  const handlePickFile = useCallback(async () => {
    try {
      const res = await DocumentPicker.getDocumentAsync({
        type: [
          'application/pdf',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'text/plain',
        ],
        copyToCacheDirectory: true,
      });
      if (res.canceled || !res.assets?.[0]) return;
      const file = res.assets[0];
      setUploadLoading(true);
      const data = await uploadStudentDoc(file.uri, file.name, file.mimeType);
      const extracted = data?.text || '';
      setUploadedDoc({ text: extracted, filename: file.name });
      if (extracted) setShareForm(p => ({ ...p, content: extracted }));
    } catch (e) {
      Alert.alert('Erreur', e.message || 'Impossible de lire le fichier');
    } finally { setUploadLoading(false); }
  }, []);

  const handleShareNote = useCallback(async () => {
    const { title, subject, content, university, year, anonymous, authorName } = shareForm;
    if (!title.trim()) { Alert.alert('Erreur', 'Le titre est obligatoire.'); return; }
    if (!content.trim() || content.trim().length < 50) {
      Alert.alert('Erreur', 'Le contenu doit faire au moins 50 caractères.'); return;
    }
    try {
      await shareNote({
        title: title.trim(), subject, contentText: content.trim(),
        university: university.trim() || null,
        studyYear: year.trim() || null,
        isAnonymous: anonymous,
        authorName: authorName.trim() || null,
      });
      Alert.alert('Partagé !', 'Ta note est maintenant disponible pour tous les étudiants.');
      setShareForm({ title: '', subject: 'droit_civil', content: '', university: '', year: '', anonymous: true, authorName: '' });
      setNotesTab('browse');
      loadNotes();
    } catch (e) {
      Alert.alert('Erreur', e.response?.data?.detail || 'Impossible de partager');
    }
  }, [shareForm, loadNotes]);

  return {
    notesModal, setNotesModal,
    notesTab, setNotesTab,
    notesList,
    activeNote, setActiveNote,
    notesLoading,
    notesSubjectFilter, setNotesSubjectFilter,
    shareForm, setShareForm,
    uploadLoading,
    uploadedDoc, setUploadedDoc,
    loadNotes, openNote,
    handlePickFile, handleShareNote,
  };
}
