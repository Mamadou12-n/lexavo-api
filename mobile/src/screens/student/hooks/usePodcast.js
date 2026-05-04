import { useState, useRef, useCallback } from 'react';
import { Alert } from 'react-native';
import { Audio } from 'expo-av';
import {
  generateStudentPodcast,
  generatePodcastAudio,
} from '../../../api/client';

export function usePodcast() {
  const [podcastResult, setPodcastResult] = useState(null);
  const [audioLoading, setAudioLoading] = useState(false);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [audioProgress, setAudioProgress] = useState({ position: 0, duration: 0 });
  const soundRef = useRef(null);

  const startPodcast = useCallback(async (topic, branch, uploadedText = '') => {
    const subject = topic.trim() || branch;
    if (!subject) return { error: 'Dis-moi ce que tu veux étudier.' };
    return { subject };
  }, []);

  const generatePodcast = useCallback(async (subject, uploadedText = '') => {
    try {
      const d = await generateStudentPodcast(subject, uploadedText);
      setPodcastResult(d);
      return d;
    } catch (e) {
      throw e;
    }
  }, []);

  const stopAudio = useCallback(async () => {
    if (soundRef.current) {
      await soundRef.current.stopAsync();
      await soundRef.current.unloadAsync();
      soundRef.current = null;
    }
    setAudioPlaying(false);
    setAudioProgress({ position: 0, duration: 0 });
  }, []);

  const handlePlayPodcast = useCallback(async (script) => {
    if (audioPlaying) {
      await stopAudio();
      return;
    }
    setAudioLoading(true);
    try {
      const lines = (script || []).map(l => `${l.speaker}: ${l.text}`).join('\n\n');
      const audioData = await generatePodcastAudio(lines);
      if (!audioData?.audio_url) {
        Alert.alert('Audio indisponible', 'La génération audio a échoué.');
        return;
      }
      await Audio.setAudioModeAsync({ playsInSilentModeIOS: true });
      const { sound } = await Audio.Sound.createAsync(
        { uri: audioData.audio_url },
        { shouldPlay: true },
        (status) => {
          if (status.isLoaded) {
            setAudioProgress({ position: status.positionMillis, duration: status.durationMillis || 0 });
            if (status.didJustFinish) {
              setAudioPlaying(false);
              setAudioProgress({ position: 0, duration: 0 });
            }
          }
        }
      );
      soundRef.current = sound;
      setAudioPlaying(true);
    } catch (e) {
      Alert.alert('Erreur audio', e.message || 'Impossible de lire le podcast');
    } finally {
      setAudioLoading(false);
    }
  }, [audioPlaying, stopAudio]);

  return {
    podcastResult, setPodcastResult,
    audioLoading,
    audioPlaying,
    audioProgress,
    startPodcast,
    generatePodcast,
    stopAudio,
    handlePlayPodcast,
  };
}
