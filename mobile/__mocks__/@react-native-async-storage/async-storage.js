/**
 * Mock manuel pour @react-native-async-storage/async-storage v3+
 * Utilisé par Jest (pas de mock intégré depuis v3)
 */

let store = {};

const AsyncStorage = {
  getItem: jest.fn((key) => Promise.resolve(store[key] ?? null)),
  setItem: jest.fn((key, value) => {
    store[key] = String(value);
    return Promise.resolve();
  }),
  removeItem: jest.fn((key) => {
    delete store[key];
    return Promise.resolve();
  }),
  clear: jest.fn(() => {
    store = {};
    return Promise.resolve();
  }),
  getAllKeys: jest.fn(() => Promise.resolve(Object.keys(store))),
  multiGet: jest.fn((keys) =>
    Promise.resolve(keys.map((k) => [k, store[k] ?? null]))
  ),
  multiSet: jest.fn((pairs) => {
    pairs.forEach(([k, v]) => { store[k] = String(v); });
    return Promise.resolve();
  }),
  multiRemove: jest.fn((keys) => {
    keys.forEach((k) => delete store[k]);
    return Promise.resolve();
  }),
};

export default AsyncStorage;
