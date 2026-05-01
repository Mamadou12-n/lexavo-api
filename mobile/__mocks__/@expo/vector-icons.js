/**
 * Mock @expo/vector-icons pour Jest.
 * Ionicons et autres icon sets → composant Text simple.
 */
const React = require('react');
const { Text } = require('react-native');

const createIconSet = () => {
  const Icon = ({ name, ...props }) => React.createElement(Text, props, name || '');
  Icon.displayName = 'MockIcon';
  return Icon;
};

module.exports = {
  Ionicons: createIconSet(),
  MaterialIcons: createIconSet(),
  FontAwesome: createIconSet(),
  Feather: createIconSet(),
  AntDesign: createIconSet(),
  Entypo: createIconSet(),
  createIconSet,
};
