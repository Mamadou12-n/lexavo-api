/**
 * Jest setup global — Lexavo Mobile
 * Chargé avant chaque suite de tests via setupFiles dans jest.config.js
 */

// Mock expo-secure-store (pas disponible en environnement Node)
jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(() => Promise.resolve(null)),
  setItemAsync: jest.fn(() => Promise.resolve()),
  deleteItemAsync: jest.fn(() => Promise.resolve()),
}));

// Mock react-native-reanimated
jest.mock('react-native-reanimated', () => {
  const Reanimated = require('react-native-reanimated/mock');
  Reanimated.default.call = () => {};
  return Reanimated;
});

// Silence console.warn dans les tests (design system warnings, etc.)
global.console.warn = jest.fn();
