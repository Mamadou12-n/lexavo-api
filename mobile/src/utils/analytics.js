/**
 * Analytics — Lexavo
 * Simple analytics module using AsyncStorage for MVP.
 * No external service needed. All events are stored locally.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = '@lexavo_analytics';

/**
 * Tracks an event with an optional properties object.
 * Events are stored as an array in AsyncStorage.
 *
 * @param {string} eventName    Name of the event (e.g. 'question_asked', 'search_performed')
 * @param {object} [properties] Optional properties to attach to the event
 */
export async function trackEvent(eventName, properties = {}) {
  try {
    const events = await _loadEvents();
    events.push({
      event: eventName,
      properties,
      timestamp: new Date().toISOString(),
    });
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(events));
  } catch (_) {
    // Silently fail — analytics should never break the app
  }
}

/**
 * Tracks a screen view event.
 *
 * @param {string} screenName  Name of the screen (e.g. 'HomeScreen', 'AskScreen')
 */
export async function trackScreen(screenName) {
  return trackEvent('screen_view', { screen: screenName });
}

/**
 * Returns all tracked events.
 *
 * @returns {Promise<Array>}  Array of event objects
 */
export async function getEvents() {
  return _loadEvents();
}

/**
 * Returns a summary of analytics data.
 *
 * @returns {Promise<object>}  Summary object with counts and breakdowns
 */
export async function getStats() {
  const events = await _loadEvents();

  const totalEvents = events.length;

  // Count screen views
  const screenViews = events.filter((e) => e.event === 'screen_view');
  const uniqueScreens = [...new Set(screenViews.map((e) => e.properties?.screen).filter(Boolean))];

  // Count questions asked
  const questionsAsked = events.filter((e) => e.event === 'question_asked').length;

  // Count searches
  const searchesPerformed = events.filter((e) => e.event === 'search_performed').length;

  // Event breakdown by type
  const eventBreakdown = {};
  events.forEach((e) => {
    eventBreakdown[e.event] = (eventBreakdown[e.event] || 0) + 1;
  });

  // Screen breakdown
  const screenBreakdown = {};
  screenViews.forEach((e) => {
    const screen = e.properties?.screen || 'unknown';
    screenBreakdown[screen] = (screenBreakdown[screen] || 0) + 1;
  });

  // First and last event timestamps
  const firstEvent = events.length > 0 ? events[0].timestamp : null;
  const lastEvent = events.length > 0 ? events[events.length - 1].timestamp : null;

  return {
    total_events: totalEvents,
    screens_viewed: uniqueScreens.length,
    total_screen_views: screenViews.length,
    questions_asked: questionsAsked,
    searches_performed: searchesPerformed,
    event_breakdown: eventBreakdown,
    screen_breakdown: screenBreakdown,
    first_event: firstEvent,
    last_event: lastEvent,
  };
}

/**
 * Clears all analytics data.
 */
export async function clearAnalytics() {
  try {
    await AsyncStorage.removeItem(STORAGE_KEY);
  } catch (_) {}
}

// ─── Internal ───────────────────────────────────────────────────────────────

async function _loadEvents() {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_) {
    return [];
  }
}
