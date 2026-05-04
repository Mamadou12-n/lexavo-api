import { useState, useCallback, useEffect } from 'react';
import {
  getStudentDashboard,
  getStudentBadges,
  getStudentLeaderboard,
  getWeakBranches,
  awardStudentXP,
} from '../../../api/client';

const XP_PER_LEVEL = 100;

export function useStudentData() {
  const [dash, setDash] = useState(null);
  const [badges, setBadges] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [weakBranches, setWeakBranches] = useState([]);
  const [lbScope, setLbScope] = useState('global');
  const [xpEarned, setXpEarned] = useState(null);
  const [newBadges, setNewBadges] = useState([]);

  const loadDashboard = useCallback(async () => {
    try {
      const [d, b, w] = await Promise.all([
        getStudentDashboard(),
        getStudentBadges(),
        getWeakBranches(),
      ]);
      setDash(d);
      setBadges(b);
      setWeakBranches(w?.branches || []);
    } catch (_) {}
  }, []);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const data = await getStudentLeaderboard(
          lbScope === 'global' ? undefined : parseInt(lbScope, 10)
        );
        setLeaderboard(data?.leaderboard || []);
      } catch (_) {}
    };
    fetchLeaderboard();
  }, [lbScope]);

  const awardXP = useCallback(async (mode, score, total) => {
    try {
      const r = await awardStudentXP(mode, score, total);
      if (r?.xp_earned) setXpEarned(r.xp_earned);
      if (r?.new_badges?.length) setNewBadges(r.new_badges);
      if (r?.xp_earned || r?.new_badges?.length) {
        setTimeout(() => { setXpEarned(null); setNewBadges([]); }, 4000);
      }
    } catch (_) {}
  }, []);

  const totalXP = dash?.total_xp || 0;
  const level = dash?.level || 1;
  const streak = dash?.streak_count || 0;
  const xpInLevel = totalXP % XP_PER_LEVEL;
  const earnedIds = badges?.earned_ids || [];

  return {
    dash, badges, leaderboard, weakBranches,
    lbScope, setLbScope,
    xpEarned, setXpEarned,
    newBadges, setNewBadges,
    awardXP, loadDashboard,
    totalXP, level, streak, xpInLevel, earnedIds,
    XP_PER_LEVEL,
  };
}
