module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    // SDK 54+ : react-native-worklets remplace react-native-reanimated/plugin
    // (worklets gère désormais le babel transform pour reanimated)
    plugins: ['react-native-worklets/plugin'],
  };
};
