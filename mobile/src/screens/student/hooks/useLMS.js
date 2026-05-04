import { useState, useCallback, useEffect } from 'react';
import { Alert } from 'react-native';
import {
  getLMSStatus,
  getLMSCourses,
  connectLMS,
  disconnectLMS,
  getLMSCourseContent,
  importLMSContent,
  getLMSUniversities,
} from '../../../api/client';

export function useLMS() {
  const [lmsConnected, setLmsConnected] = useState(false);
  const [lmsSiteName, setLmsSiteName] = useState('');
  const [lmsFullname, setLmsFullname] = useState('');
  const [lmsCourses, setLmsCourses] = useState([]);
  const [lmsCourseContent, setLmsCourseContent] = useState([]);
  const [lmsActiveCourse, setLmsActiveCourse] = useState(null);
  const [lmsTab, setLmsTab] = useState('connect');
  const [lmsModal, setLmsModal] = useState(false);
  const [lmsUrl, setLmsUrl] = useState('');
  const [lmsUser, setLmsUser] = useState('');
  const [lmsPass, setLmsPass] = useState('');
  const [lmsLoading, setLmsLoading] = useState(false);
  const [lmsError, setLmsError] = useState('');
  const [lmsUniversities, setLmsUniversities] = useState([]);

  const loadLMSStatus = useCallback(async () => {
    try {
      const s = await getLMSStatus();
      setLmsConnected(s.connected);
      if (s.connected) {
        setLmsSiteName(s.site_name || '');
        setLmsFullname(s.user_fullname || '');
      }
    } catch (_) {}
  }, []);

  useEffect(() => { loadLMSStatus(); }, [loadLMSStatus]);

  const loadLMSCourses = useCallback(async () => {
    setLmsLoading(true); setLmsError('');
    try {
      const d = await getLMSCourses();
      setLmsCourses(d?.courses || []);
      setLmsTab('courses');
    } catch (e) {
      setLmsError(e.response?.data?.detail || e.message);
    } finally { setLmsLoading(false); }
  }, []);

  const handleLMSConnect = useCallback(async () => {
    if (!lmsUrl.trim() || !lmsUser.trim() || !lmsPass) {
      setLmsError('Remplis tous les champs'); return;
    }
    setLmsLoading(true); setLmsError('');
    try {
      const r = await connectLMS(lmsUrl.trim(), lmsUser.trim(), lmsPass);
      setLmsConnected(true);
      setLmsSiteName(r.site_name || '');
      setLmsFullname(r.user_fullname || '');
      setLmsPass('');
      Alert.alert('Connecté !', `${r.site_name}\n${r.user_fullname}`);
      loadLMSCourses();
    } catch (e) {
      setLmsError(e.response?.data?.detail || e.message || 'Échec de connexion');
    } finally { setLmsLoading(false); }
  }, [lmsUrl, lmsUser, lmsPass, loadLMSCourses]);

  const handleLMSDisconnect = useCallback(() => {
    Alert.alert('Déconnexion', 'Tu perdras l\'accès à tes cours importés.', [
      { text: 'Annuler' },
      {
        text: 'Déconnecter', style: 'destructive', onPress: async () => {
          try {
            await disconnectLMS();
            setLmsConnected(false); setLmsCourses([]); setLmsSiteName('');
            setLmsFullname(''); setLmsTab('connect');
          } catch (_) {}
        },
      },
    ]);
  }, []);

  const openCourseContent = useCallback(async (course) => {
    setLmsActiveCourse(course);
    setLmsLoading(true); setLmsError('');
    try {
      const d = await getLMSCourseContent(course.id);
      setLmsCourseContent(d?.sections || []);
      setLmsTab('content');
    } catch (e) {
      setLmsError(e.response?.data?.detail || e.message);
    } finally { setLmsLoading(false); }
  }, []);

  const handleImportFile = useCallback(async (fileUrl, courseName, courseId) => {
    setLmsLoading(true); setLmsError('');
    try {
      const r = await importLMSContent(fileUrl, courseId, courseName);
      Alert.alert('Importé !', `${r.content_length} caractères extraits.\nCe contenu sera utilisé pour tes quiz et flashcards.`);
    } catch (e) {
      setLmsError(e.response?.data?.detail || e.message);
    } finally { setLmsLoading(false); }
  }, []);

  const fetchLMSUniversities = useCallback(async () => {
    try {
      const d = await getLMSUniversities();
      setLmsUniversities(d?.universities || []);
    } catch (_) {}
  }, []);

  return {
    lmsConnected, lmsSiteName, lmsFullname,
    lmsCourses, lmsCourseContent, lmsActiveCourse,
    lmsTab, setLmsTab,
    lmsModal, setLmsModal,
    lmsUrl, setLmsUrl,
    lmsUser, setLmsUser,
    lmsPass, setLmsPass,
    lmsLoading, lmsError,
    lmsUniversities,
    loadLMSStatus, loadLMSCourses,
    handleLMSConnect, handleLMSDisconnect,
    openCourseContent, handleImportFile,
    fetchLMSUniversities,
  };
}
