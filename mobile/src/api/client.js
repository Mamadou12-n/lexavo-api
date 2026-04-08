/**
 * API Client — Lexavo
 * Communique avec le backend FastAPI (api/main.py)
 *
 * Endpoints :
 *   POST /ask    → Question juridique → réponse RAG + sources
 *   POST /search → Recherche vectorielle seule
 *   GET  /health → Statut API + index
 *   GET  /stats  → Statistiques base documentaire
 *   POST /auth/register  → Inscription
 *   POST /auth/login     → Connexion JWT
 *   GET  /auth/me        → Profil utilisateur
 */

import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// ─── Clés AsyncStorage ────────────────────────────────────────────────────────
const DEFAULT_API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'https://lexavo-api-production.up.railway.app';
const API_URL_KEY     = '@lexavo_api_url';
const AUTH_TOKEN_KEY    = '@lexavo_auth_token';
const AUTH_USER_KEY     = '@lexavo_auth_user';
const REFRESH_TOKEN_KEY = '@lexavo_refresh_token';
export const REGION_KEY = '@lexavo_region'; // bruxelles | wallonie | flandre
export const LANG_KEY   = 'lexavo_lang';    // fr | nl | de | en | es | it | pt | ar

let _baseURL   = DEFAULT_API_URL;
let _authToken = null;   // JWT en mémoire
let _onUnauth  = null;   // callback appelé sur 401 → logout
let _lang      = 'fr';   // langue de réponse courante

export async function setLanguage(code) {
  _lang = code;
  await AsyncStorage.setItem(LANG_KEY, code);
}

export async function initLanguage() {
  try {
    const saved = await AsyncStorage.getItem(LANG_KEY);
    if (saved) _lang = saved;
  } catch (_) {}
}

// ─── Instance axios ───────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: _baseURL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Intercepteur requête : injecte le JWT si disponible
api.interceptors.request.use((config) => {
  if (_authToken) {
    config.headers['Authorization'] = `Bearer ${_authToken}`;
  }
  return config;
});

// Intercepteur réponse : gère les 401 → tente refresh avant logout
let _isRefreshing = false;
let _refreshQueue = [];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && _authToken && !originalRequest._retry) {
      // Tenter un refresh token avant de logout
      if (_isRefreshing) {
        return new Promise((resolve, reject) => {
          _refreshQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers['Authorization'] = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      _isRefreshing = true;

      try {
        const rt = await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
        if (rt) {
          const res = await axios.post(`${_baseURL}/auth/refresh`, { refresh_token: rt });
          const { token, refresh_token: newRt } = res.data;

          _authToken = token;
          await AsyncStorage.setItem(AUTH_TOKEN_KEY, token);
          await AsyncStorage.setItem(REFRESH_TOKEN_KEY, newRt);

          // Résoudre toutes les requêtes en attente
          _refreshQueue.forEach((q) => q.resolve(token));
          _refreshQueue = [];
          _isRefreshing = false;

          originalRequest.headers['Authorization'] = `Bearer ${token}`;
          return api(originalRequest);
        }
      } catch (_refreshErr) {
        _refreshQueue.forEach((q) => q.reject(_refreshErr));
        _refreshQueue = [];
        _isRefreshing = false;
      }

      // Refresh échoué → logout
      _authToken = null;
      await AsyncStorage.multiRemove([AUTH_TOKEN_KEY, AUTH_USER_KEY, REFRESH_TOKEN_KEY]).catch(() => {});
      if (_onUnauth) _onUnauth();
    }
    return Promise.reject(error);
  }
);

/**
 * Enregistre un callback appelé quand l'API retourne 401.
 * Utilisé par App.js pour rediriger vers l'écran de connexion.
 */
export function setUnauthHandler(fn) {
  _onUnauth = fn;
}

// ─── URL API ──────────────────────────────────────────────────────────────────

export async function initApiUrl() {
  try {
    const stored = await AsyncStorage.getItem(API_URL_KEY);
    // Toujours utiliser l'URL production — ignorer les anciennes valeurs localhost
    if (stored && !stored.includes('localhost') && !stored.includes('10.0.2.2') && !stored.includes('127.0.0.1')) {
      _baseURL = stored;
      api.defaults.baseURL = stored;
    } else {
      // Forcer l'URL production
      _baseURL = DEFAULT_API_URL;
      api.defaults.baseURL = DEFAULT_API_URL;
      await AsyncStorage.setItem(API_URL_KEY, DEFAULT_API_URL);
    }
  } catch (_) {
    _baseURL = DEFAULT_API_URL;
    api.defaults.baseURL = DEFAULT_API_URL;
  }
}

export async function setApiUrl(url) {
  const clean = url.replace(/\/$/, '');
  _baseURL = clean;
  api.defaults.baseURL = clean;
  await AsyncStorage.setItem(API_URL_KEY, clean);
}

export function getApiUrl() {
  return _baseURL;
}

// ─── Authentification ─────────────────────────────────────────────────────────

/**
 * Charge le JWT depuis AsyncStorage au démarrage.
 * Retourne true si un token valide est trouvé.
 */
export async function initAuthToken() {
  try {
    const token = await AsyncStorage.getItem(AUTH_TOKEN_KEY);
    if (token) {
      _authToken = token;
      return true;
    }
  } catch (_) {}
  return false;
}

export function getAuthToken() {
  return _authToken;
}

/**
 * Inscription d'un nouvel utilisateur.
 * Stocke automatiquement le JWT retourné.
 */
export async function register(email, password, name = '', language = 'fr') {
  const response = await api.post('/auth/register', { email, password, name, language });
  const { token, user, refresh_token } = response.data;
  _authToken = token;
  await AsyncStorage.setItem(AUTH_TOKEN_KEY, token);
  await AsyncStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
  if (refresh_token) await AsyncStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
  return response.data;
}

/**
 * Connexion — retourne un JWT access token + refresh token.
 * Stocke automatiquement les deux tokens.
 */
export async function login(email, password) {
  const response = await api.post('/auth/login', { email, password });
  const { token, user, refresh_token } = response.data;
  _authToken = token;
  await AsyncStorage.setItem(AUTH_TOKEN_KEY, token);
  await AsyncStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
  if (refresh_token) await AsyncStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
  return response.data;
}

/**
 * Demande de reset de mot de passe — envoie l'email.
 */
export async function forgotPassword(email) {
  const response = await api.post('/auth/forgot-password', { email });
  return response.data;
}

/**
 * Reset du mot de passe avec token reçu.
 */
export async function resetPassword(token, newPassword) {
  const response = await api.post('/auth/reset-password', { token, new_password: newPassword });
  return response.data;
}

/**
 * Déconnexion — supprime le JWT de la mémoire et d'AsyncStorage.
 */
export async function logout() {
  _authToken = null;
  await AsyncStorage.multiRemove([AUTH_TOKEN_KEY, AUTH_USER_KEY, REFRESH_TOKEN_KEY]).catch(() => {});
}

/**
 * Charge le profil utilisateur depuis le cache local.
 */
export async function getCachedUser() {
  try {
    const raw = await AsyncStorage.getItem(AUTH_USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

/**
 * Récupère le profil depuis l'API (nécessite token valide).
 */
export async function getMe() {
  const r = await api.get('/auth/me');
  return r.data;
}

// ─── Endpoints ───────────────────────────────────────────────────────────────

/**
 * POST /ask — Question juridique → réponse RAG complète.
 *
 * @param {string} question
 * @param {object} opts
 * @param {number} opts.top_k         Nombre de chunks contextuels (défaut: 6)
 * @param {string} opts.source_filter Filtrer par source (ex: "HUDOC")
 * @param {string} opts.model         Modèle Claude (défaut: claude-haiku)
 *
 * @returns {{ answer, sources, chunks_used, model }}
 */
export async function askQuestion(question, opts = {}) {
  // Lire la région stockée lors de l'onboarding (si non forcée dans opts)
  let region = opts.region ?? null;
  if (!region) {
    try { region = await AsyncStorage.getItem(REGION_KEY); } catch (_) {}
  }

  const photos = opts.photos ?? [];
  const payload = {
    question,
    top_k: opts.top_k ?? 6,
    // L'API attend List[str] — encapsuler le filtre string en tableau
    ...(opts.source_filter && {
      source_filter: Array.isArray(opts.source_filter)
        ? opts.source_filter
        : [opts.source_filter],
    }),
    ...(opts.model  && { model: opts.model }),
    ...(region      && { region }),
    ...(opts.conversation_id && { conversation_id: opts.conversation_id }),
    photos_base64: photos.map(p => p.base64).filter(Boolean),
    language: opts.language ?? _lang ?? 'fr',
  };
  const response = await api.post('/ask', payload);
  return response.data;
}

/**
 * POST /search — Recherche vectorielle pure (sans LLM).
 *
 * @param {string} query
 * @param {object} opts
 * @param {number} opts.top_k
 * @param {string} opts.source_filter
 *
 * @returns {{ query, results, total }}
 */
export async function searchDocuments(query, opts = {}) {
  const payload = {
    query,
    top_k: opts.top_k ?? 10,
    // L'API attend List[str] — encapsuler le filtre string en tableau
    ...(opts.source_filter && {
      source_filter: Array.isArray(opts.source_filter)
        ? opts.source_filter
        : [opts.source_filter],
    }),
  };
  const response = await api.post('/search', payload);
  return response.data;
}

/**
 * GET /health — Vérifie que l'API et l'index ChromaDB sont opérationnels.
 *
 * @returns {{ status, api_version, index, anthropic_key_set }}
 */
export async function checkHealth() {
  const response = await api.get('/health');
  return response.data;
}

/**
 * GET /stats — Statistiques de la base documentaire.
 *
 * @returns {{ status, total_chunks, total_documents, sources, ... }}
 */
export async function getStats() {
  const response = await api.get('/stats');
  return response.data;
}

// ─── Sources disponibles (pour filtrage) ─────────────────────────────────────
export const SOURCES = [
  { key: null,               label: 'Toutes les sources',         emoji: '🔍' },
  { key: 'HUDOC',            label: 'HUDOC — CEDH',               emoji: '🇪🇺' },
  { key: 'EUR-Lex',          label: 'EUR-Lex — CJUE',             emoji: '⚖️' },
  { key: 'Juridat',          label: 'Juridat — Cassation BE',     emoji: '🏛️' },
  { key: 'Moniteur belge',   label: 'Moniteur belge',             emoji: '📜' },
  { key: 'Cour constitutionnelle', label: 'Cour constitutionnelle', emoji: '📋' },
  { key: "Conseil d'État",   label: "Conseil d'État",             emoji: '🏢' },
  { key: 'CCE',              label: 'CCE — Étrangers',            emoji: '🌍' },
  { key: 'CNT',              label: 'CNT — Droit social',         emoji: '👷' },
  { key: 'JUSTEL',           label: 'JUSTEL — Codes',             emoji: '📚' },
  { key: 'APD',              label: 'APD — RGPD',                 emoji: '🔒' },
  { key: 'GalliLex',         label: 'GalliLex — FWB',             emoji: '🎓' },
  { key: 'FSMA',             label: 'FSMA — Finance',             emoji: '💹' },
  { key: 'WalLex',           label: 'WalLex — Wallonie',          emoji: '🌿' },
  { key: 'Cour des comptes', label: 'Cour des comptes',           emoji: '🔎' },
  { key: 'Chambre',          label: 'Chambre des représentants',  emoji: '🏛️' },
  { key: 'Codex Vlaanderen', label: 'Codex Vlaanderen — Flandre', emoji: '🦁' },
  { key: 'Bruxelles',        label: 'Bruxelles — Région',         emoji: '🏙️' },
  { key: 'SPF Finances',     label: 'SPF Finances — Fiscalité',   emoji: '💰' },
];

// ─── Lexavo Features ─────────────────────────────────────────────────────────

export async function shieldAnalyze(payload) {
  const r = await api.post('/shield/analyze', payload);
  return r.data;
}

export async function getDefendCategories() {
  const r = await api.get('/defend/categories');
  return r.data;
}

export async function defendAnalyze(description, category = null, region = null, user_name = '', photos = []) {
  const r = await api.post('/defend/analyze', {
    description, category, region, user_name,
    photos_base64: photos.map(p => p.base64).filter(Boolean),
  });
  return r.data;
}

export async function defendChecklist(category, answers, region = null, description = '', photos = [], tone = 'formel') {
  const r = await api.post('/defend/checklist', {
    category, answers, region, description, tone,
    photos: photos.map(p => p.base64).filter(Boolean),
  });
  return r.data;
}

export async function regenerateDefendLetter(description, vicesStr, legalContext, tone) {
  const r = await api.post('/defend/regenerate-letter', {
    description, vices_str: vicesStr, legal_context: legalContext, tone,
  });
  return r.data;
}

export async function scanAmende(photos = [], category = 'amende') {
  const r = await api.post('/defend/scan-amende', {
    photos: photos.map(p => p.base64).filter(Boolean),
    category,
  });
  return r.data;
}

// Pas d'endpoint /calculators/list — les calculateurs sont fixes (notice-period / alimony / succession)
export async function listCalculators() {
  return {
    calculators: [
      { id: 'preavis',              name: 'Délai de préavis' },
      { id: 'pension_alimentaire',  name: 'Pension alimentaire' },
      { id: 'droits_succession',    name: 'Droits de succession' },
    ],
  };
}

/**
 * Calcule selon le type :
 *   notice_period → POST /calculators/notice-period
 *   alimony       → POST /calculators/alimony
 *   succession    → POST /calculators/succession
 *   vacation_pay  → POST /calculators/vacation-pay
 */
export async function runCalculator(calc_type, params) {
  const routes = {
    preavis:             '/calculators/notice-period',
    pension_alimentaire: '/calculators/alimony',
    droits_succession:   '/calculators/succession',
  };
  const route = routes[calc_type] ?? `/calculators/${calc_type.replace(/_/g, '-')}`;
  const r = await api.post(route, params);
  return r.data;
}

export async function listContractTemplates() {
  const r = await api.get('/contracts/templates');
  return r.data;
}

export async function generateContract(template_id, variables) {
  // Backend : POST /contracts/{template_id}/generate — variables MUST be wrapped
  const r = await api.post(`/contracts/${template_id}/generate`, { variables });
  return r.data;
}

export async function generateLegalResponse(received_text, user_context = '', tone = 'formal') {
  // Backend : POST /response/generate — aligned with backend field names
  const r = await api.post('/response/generate', { received_text, user_context, tone });
  return r.data;
}

export async function runDiagnostic(answers, user_type = 'particulier') {
  // Backend : POST /diagnostic/analyze — sends answers array
  const r = await api.post('/diagnostic/analyze', { answers, user_type });
  return r.data;
}

export async function getScoreQuestions() {
  const r = await api.get('/score/questions');
  return r.data;
}

export async function evaluateScore(answers) {
  const r = await api.post('/score/evaluate', { answers });
  return r.data;
}

export async function getComplianceQuestions() {
  const r = await api.get('/compliance/questions');
  return r.data;
}

export async function runComplianceAudit(company_type, answers) {
  const r = await api.post('/compliance/audit', { company_type, answers });
  return r.data;
}

export async function getAlertDomains() {
  const r = await api.get('/alerts/domains');
  return r.data;
}

export async function saveAlertPreferences(domains) {
  const r = await api.post('/alerts/preferences', { domains });
  return r.data;
}

export async function getAlertFeed(domains = []) {
  const r = await api.get('/alerts/feed', { params: { domains: domains.join(','), limit: 10 } });
  return r.data;
}

export async function decodeDocument(document_text, language = 'fr', photos = []) {
  // Backend reads: document_text (not text)
  const r = await api.post('/decode/analyze', {
    document_text, language,
    photos_base64: photos.map(p => p.base64).filter(Boolean),
  });
  return r.data;
}

export async function getLitigationStages() {
  const r = await api.get('/litigation/stages');
  return r.data;
}

export async function startLitigation(payload, photos = []) {
  const r = await api.post('/litigation/start', {
    ...payload,
    photos_base64: photos.map(p => p.base64).filter(Boolean),
  });
  return r.data;
}

export async function findMatchingLawyers(description, city = '', language = 'fr', budget = '') {
  // Backend reads: description, city, language, budget
  const r = await api.post('/match/find', { description, city, language, budget });
  return r.data;
}

export async function getEmergencyCategories() {
  const r = await api.get('/emergency/categories');
  return r.data;
}

export async function createEmergencyRequest(category, description, phone, city = '', photos = []) {
  // Backend reads: category, description, phone, city (not contact_email)
  const r = await api.post('/emergency/request', {
    category, description, phone, city,
    photos_base64: photos.map(p => p.base64).filter(Boolean),
  });
  return r.data;
}

export async function createProofCase(title, description) {
  const r = await api.post('/proof/create', { title, description });
  return r.data;
}

export async function addProofEntry(case_id, type, content, metadata = '') {
  // Backend reads: type, content, metadata (not entry_type, description, date)
  const r = await api.post(`/proof/${case_id}/add-entry`, { type, content, metadata });
  return r.data;
}

export async function getHeritageGuide(region, estimated_value, relationship, has_testament = false, has_real_estate = false) {
  // Backend reads: region, estimated_value, relationship, has_testament, has_real_estate
  const r = await api.post('/heritage/guide', { region, estimated_value, relationship, has_testament, has_real_estate });
  return r.data;
}

export async function askFiscal(question, context = '', photos = []) {
  const photos_base64 = photos.map(p => p.base64).filter(Boolean);
  const r = await api.post('/fiscal/ask', { question, context, photos_base64 });
  return r.data;
}

// ─── Audit Entreprise ────────────────────────────────────────────────────────

export async function getAuditQuestions(companyType = 'srl') {
  const r = await api.get(`/audit/questions?company_type=${companyType}`);
  return r.data;
}

export async function generateAudit(body) {
  const r = await api.post('/audit/generate', body);
  return r.data;
}

export async function getAuditHistory() {
  const r = await api.get('/audit/history');
  return r.data;
}

// ─── Student (quiz, flashcards, résumés) ─────────────────────────────────────

export async function getStudentBranches() {
  const r = await api.get('/student/branches');
  return r.data;
}

export async function generateQuiz(branch, difficulty = 'moyen', numQuestions = 10, documentContent = '') {
  const r = await api.post('/student/quiz', { branch, difficulty, num_questions: numQuestions, ...(documentContent ? { document_content: documentContent } : {}) });
  return r.data;
}

export async function generateFlashcards(branch, topic = '', numCards = 12, documentContent = '') {
  const r = await api.post('/student/flashcards', { branch, topic, num_cards: numCards, ...(documentContent ? { document_content: documentContent } : {}) });
  return r.data;
}

export async function generateSummary(branch, topic = '', documentContent = '') {
  const r = await api.post('/student/summary', { branch, topic: topic || branch, ...(documentContent ? { document_content: documentContent } : {}) });
  return r.data;
}

// ─── Student Gamification ─────────────────────────────────────────────────────

export async function getStudentDashboard() {
  const r = await api.get('/student/dashboard');
  return r.data;
}

export async function postStudentActivity(mode, branch, score, total) {
  const r = await api.post('/student/activity', { mode, branch, score, total });
  return r.data;
}

export async function getStudentLeaderboard(scope = 'global', groupId = '') {
  const params = { scope };
  if (groupId) params.group_id = groupId;
  const r = await api.get('/student/leaderboard', { params });
  return r.data;
}

export async function generateCaseStudy(branch, difficulty = 'moyen') {
  const r = await api.post('/student/case-study', { branch, difficulty });
  return r.data;
}

export async function evaluateCaseStudy(caseData, answer) {
  const r = await api.post('/student/case-study/evaluate', { case_data: caseData, answer });
  return r.data;
}

export async function generateMockExam(branches, numQuestions = 20) {
  const r = await api.post('/student/mock-exam', { branches, num_questions: numQuestions });
  return r.data;
}

export async function submitMockExam(examData, answers) {
  const r = await api.post('/student/mock-exam/submit', { exam_data: examData, answers });
  return r.data;
}

export async function getStudentBadges() {
  const r = await api.get('/student/badges');
  return r.data;
}

export async function getStudentWeakBranches() {
  const r = await api.get('/student/weak-branches');
  return r.data;
}

export async function generateFreeRecall(branch, documentContent = '') {
  const r = await api.post('/student/free-recall', { branch, ...(documentContent ? { document_content: documentContent } : {}) });
  return r.data;
}

export async function evaluateFreeRecall(questionData, answer) {
  const r = await api.post('/student/free-recall/evaluate', { question_data: questionData, answer });
  return r.data;
}

export async function generateInterleavedQuiz(branches, numPerBranch = 3) {
  const r = await api.post('/student/interleaved-quiz', { branches, num_per_branch: numPerBranch });
  return r.data;
}

export async function createStudentGroup(name) {
  const r = await api.post('/student/groups', { name });
  return r.data;
}

export async function joinStudentGroup(code) {
  const r = await api.post('/student/groups/join', { code });
  return r.data;
}

export async function getStudentGroups() {
  const r = await api.get('/student/groups');
  return r.data;
}

// ─── LMS Integration (Moodle / Canvas) ────────────────────────────────────────

export async function getLMSUniversities() {
  const r = await api.get('/student/lms/universities');
  return r.data;
}

export async function connectLMS(siteUrl, username, password, platform = 'moodle') {
  const r = await api.post('/student/lms/connect', {
    site_url: siteUrl, username, password, platform,
  });
  return r.data;
}

export async function getLMSStatus() {
  const r = await api.get('/student/lms/status');
  return r.data;
}

export async function getLMSCourses() {
  const r = await api.get('/student/lms/courses');
  return r.data;
}

export async function getLMSCourseContent(courseId) {
  const r = await api.get(`/student/lms/course/${courseId}/content`);
  return r.data;
}

export async function importLMSContent(fileUrl, courseId, courseName) {
  const r = await api.post('/student/lms/import', {
    file_url: fileUrl, course_id: courseId, course_name: courseName,
  });
  return r.data;
}

export async function disconnectLMS() {
  const r = await api.delete('/student/lms/disconnect');
  return r.data;
}

// ─── Notes partagées (bibliothèque communautaire) ─────────────────────────────

export async function shareNote({ title, subject, contentText, university, studyYear, isAnonymous, authorName, fileType }) {
  const r = await api.post('/student/notes/share', {
    title, subject, content_text: contentText, university, study_year: studyYear,
    is_anonymous: isAnonymous, author_name: authorName, file_type: fileType || 'text',
  });
  return r.data;
}

export async function listSharedNotes(subject = null, university = null, limit = 50, offset = 0) {
  const params = { limit, offset };
  if (subject) params.subject = subject;
  if (university) params.university = university;
  const r = await api.get('/student/notes', { params });
  return r.data;
}

export async function getSharedNote(noteId) {
  const r = await api.get(`/student/notes/${noteId}`);
  return r.data;
}

export async function likeSharedNote(noteId) {
  const r = await api.post(`/student/notes/${noteId}/like`);
  return r.data;
}

export async function deleteSharedNote(noteId) {
  const r = await api.delete(`/student/notes/${noteId}`);
  return r.data;
}

export async function uploadNoteFile(fileUri, fileName, mimeType) {
  const formData = new FormData();
  formData.append('file', { uri: fileUri, name: fileName, type: mimeType });
  const token = await AsyncStorage.getItem(AUTH_TOKEN_KEY);
  const baseURL = api.defaults.baseURL;
  const response = await fetch(`${baseURL}/student/notes/upload-file`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      'Content-Type': 'multipart/form-data',
    },
    body: formData,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Erreur upload (${response.status})`);
  }
  return response.json();
}

// ─── Billing (routes /billing/* — alignées sur le backend) ────────────────────

export async function getSubscriptionStatus() {
  // Backend : GET /billing/subscription (auth JWT requise — user identifié par token)
  const r = await api.get('/billing/subscription');
  return r.data;
}

export async function getBillingPlans() {
  const r = await api.get('/billing/plans');
  return r.data;
}

export async function createCheckoutSession(plan, billing = 'monthly') {
  // Backend : POST /billing/checkout — plan + billing (monthly|annual)
  const r = await api.post('/billing/checkout', { plan, billing });
  return r.data; // { checkout_url, session_id }
}

export async function openBillingPortal() {
  // Backend : POST /billing/portal — portail Stripe pour gérer l'abonnement
  const r = await api.post('/billing/portal');
  return r.data; // { portal_url }
}

export async function cancelSubscription() {
  // Backend : POST /billing/cancel — annule à la fin de la période
  const r = await api.post('/billing/cancel');
  return r.data;
}

export async function restoreSubscription() {
  // Backend : POST /billing/restore — réactive si cancel_at_period_end=True
  const r = await api.post('/billing/restore');
  return r.data;
}

// ─── Push Notifications ───────────────────────────────────────────────────────

export async function registerPushToken(token) {
  // Backend : POST /notifications/register
  const r = await api.post('/notifications/register', { token });
  return r.data;
}

export async function updateNotificationPreferences(token, preferences) {
  // Backend : POST /notifications/preferences
  const r = await api.post('/notifications/preferences', { token, preferences });
  return r.data;
}

// ─── Conversations ────────────────────────────────────────────────────────────

/**
 * GET /conversations — Liste des conversations de l'utilisateur connecté.
 * @returns {{ conversations: ConversationResponse[], total: number }}
 */
export async function getConversations() {
  const r = await api.get('/conversations');
  return r.data;
}

/**
 * GET /conversations/{id}/messages — Messages d'une conversation.
 * @param {number} conversationId
 * @returns {{ messages: MessageResponse[], total: number }}
 */
export async function getConversationMessages(conversationId) {
  const r = await api.get(`/conversations/${conversationId}/messages`);
  return r.data;
}

// ─── User Context ─────────────────────────────────────────────────────────────

/**
 * GET /user/context — Recuperer le contexte utilisateur (region, profession, langue).
 */
export async function getUserContext() {
  const r = await api.get('/user/context');
  return r.data;
}

/**
 * PUT /user/context — Mettre a jour le contexte utilisateur.
 * @param {{ region?: string, profession?: string, language?: string }} ctx
 */
export async function updateUserContext(ctx) {
  const r = await api.put('/user/context', ctx);
  return r.data;
}

export default api;
