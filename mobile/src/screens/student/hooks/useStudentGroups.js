import { useState, useCallback } from 'react';
import { Alert } from 'react-native';
import {
  getStudentGroups,
  createStudentGroup,
  joinStudentGroup,
} from '../../../api/client';

export function useStudentGroups() {
  const [groups, setGroups] = useState([]);
  const [groupModal, setGroupModal] = useState(false);
  const [groupTab, setGroupTab] = useState('list');
  const [groupName, setGroupName] = useState('');
  const [joinCode, setJoinCode] = useState('');

  const loadGroups = useCallback(async () => {
    try {
      const g = await getStudentGroups();
      setGroups(g?.groups || []);
    } catch (_) {}
  }, []);

  const handleCreateGroup = useCallback(async () => {
    if (!groupName.trim()) return;
    try {
      const g = await createStudentGroup(groupName.trim());
      Alert.alert('Groupe créé !', `Code d'invitation : ${g.code}\nPartage ce code avec tes amis.`);
      setGroupName('');
      setGroupTab('list');
      loadGroups();
    } catch (e) {
      Alert.alert('Erreur', e.message);
    }
  }, [groupName, loadGroups]);

  const handleJoinGroup = useCallback(async () => {
    if (!joinCode.trim()) return;
    try {
      await joinStudentGroup(joinCode.trim().toUpperCase());
      Alert.alert('Rejoint !', 'Tu as rejoint le groupe.');
      setJoinCode('');
      setGroupTab('list');
      loadGroups();
    } catch (e) {
      Alert.alert('Erreur', e.message);
    }
  }, [joinCode, loadGroups]);

  return {
    groups,
    groupModal, setGroupModal,
    groupTab, setGroupTab,
    groupName, setGroupName,
    joinCode, setJoinCode,
    loadGroups,
    handleCreateGroup,
    handleJoinGroup,
  };
}
