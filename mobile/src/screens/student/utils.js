/**
 * StudentScreen — utilitaires extraits (refactor SAFE)
 *
 * Exporte :
 *  - XP_PER_LEVEL : palier d'XP par niveau
 *  - MODES        : liste des 9 modes d'apprentissage (constants UI)
 *  - fmtTime      : formate un nombre de secondes en mm:ss
 *  - getQuizScore : calcule le score d'un quiz à partir des réponses sélectionnées
 *
 * Le thème T et la feuille de styles s restent dans StudentScreen.js
 * car ils référencent SW (Dimensions) et sont utilisés par mdStyle inline.
 */

export const XP_PER_LEVEL = 500;

/**
 * Formate une durée en secondes au format mm:ss (zero-padded).
 * @param {number} seconds
 * @returns {string}
 */
export const fmtTime = (seconds) =>
  `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;

/**
 * Calcule le score d'un quiz : nombre de réponses correctes / total.
 * @param {{questions?: Array<{id: string, correct: any}>}|null} result
 * @param {Record<string, any>} selectedAnswers
 * @returns {{correct: number, total: number}}
 */
export const computeQuizScore = (result, selectedAnswers) => {
  if (!result?.questions) return { correct: 0, total: 0 };
  let correct = 0;
  result.questions.forEach((q) => {
    if (selectedAnswers[q.id] === q.correct) correct++;
  });
  return { correct, total: result.questions.length };
};

/**
 * Liste des 9 modes d'apprentissage Lexavo Campus.
 * Chaque mode définit son label, sous-titre, gradient, icône et XP associé.
 */
export const MODES = [
  { id: 'quiz', label: 'Quiz IA', sub: 'L\'IA s\'adapte à ton niveau.', gradient: ['#4A1D96', '#8B5CF6'], glowColor: 'rgba(139, 92, 246, 0.25)', icon: '⚡', badge: '+50 XP', xpMode: 'quiz_pass' },
  { id: 'flashcards', label: 'Flashcards SRS', sub: 'Algorithme Leitner. Mémorise moins, retiens plus.', gradient: ['#004D8F', '#4DA6FF'], glowColor: 'rgba(77, 166, 255, 0.25)', icon: '🃏', badge: '+20 XP', xpMode: 'flashcards' },
  { id: 'summary', label: 'Résumé Turbo', sub: 'Des heures de cours en 30 secondes.', gradient: ['#991B1B', '#FF6B6B'], glowColor: 'rgba(255, 107, 107, 0.25)', icon: '🚀', badge: '+10 XP', xpMode: 'summary' },
  { id: 'chat', label: 'Tuteur IA', sub: 'Ton prof 24/7. Pose n\'importe quelle question.', gradient: ['#004D40', '#00D4AA'], glowColor: 'rgba(0, 212, 170, 0.25)', icon: '🤖', badge: 'ILLIMITÉ', xpMode: null },
  { id: 'podcast', label: 'Podcast IA', sub: 'Script dialogue 2 hosts + export NotebookLM.', gradient: ['#7C4D00', '#FFB84D'], glowColor: 'rgba(255, 184, 77, 0.25)', icon: '🎙️', badge: '+10 XP', xpMode: 'summary' },
  { id: 'case_study', label: 'Cas Pratique', sub: 'Résoudre un cas réel. Correction IA enrichie.', gradient: ['#1A4731', '#2DD4BF'], glowColor: 'rgba(45, 212, 191, 0.25)', icon: '🧠', badge: '+75 XP', xpMode: 'case_study' },
  { id: 'mock_exam', label: 'Examen Blanc', sub: '20 questions chrono. Solo ou groupe.', gradient: ['#4A1A1A', '#E53E3E'], glowColor: 'rgba(229, 62, 62, 0.25)', icon: '📝', badge: '+150 XP', xpMode: 'mock_exam' },
  { id: 'interleaved', label: 'Révision Mixte', sub: 'Mélange de branches. +50% de rétention prouvé.', gradient: ['#1A1A4A', '#6366F1'], glowColor: 'rgba(99, 102, 241, 0.25)', icon: '🔀', badge: '+50 XP', xpMode: 'quiz_pass' },
  { id: 'free_recall', label: 'Rappel Libre', sub: 'Question ouverte. ×2 rétention vs QCM.', gradient: ['#2D1A4A', '#A855F7'], glowColor: 'rgba(168, 85, 247, 0.25)', icon: '✍️', badge: '+75 XP', xpMode: 'free_recall' },
];
