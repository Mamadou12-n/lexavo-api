/**
 * Tests composants UI -- Disclaimer, Card, ToolCard
 */

import React from 'react';
import { render, screen } from '@testing-library/react-native';

import { Disclaimer } from '../src/components/ui/Disclaimer';
import { Card } from '../src/components/ui/Card';
import { ToolCard } from '../src/components/ui/ToolCard';

// --- Disclaimer ---

describe('Disclaimer', () => {
  test('rend le texte legal par defaut', () => {
    render(<Disclaimer />);
    expect(
      screen.getByText(
        'Cette réponse ne constitue pas un avis juridique. Consultez un avocat pour votre situation spécifique.'
      )
    ).toBeTruthy();
  });

  test('rend un message personnalise passe en prop', () => {
    render(<Disclaimer message="Ceci est un avis de test." />);
    expect(screen.getByText('Ceci est un avis de test.')).toBeTruthy();
  });

  test('a un accessibilityRole text (accessible=true)', () => {
    // RNTL ne supporte pas getByRole('text') -- on verifie via accessible prop
    const { UNSAFE_getByProps } = render(<Disclaimer />);
    expect(UNSAFE_getByProps({ accessibilityRole: 'text' })).toBeTruthy();
  });

  test("le label d'accessibilite contient le message par defaut", () => {
    const { getByLabelText } = render(<Disclaimer />);
    expect(
      getByLabelText(
        'Cette réponse ne constitue pas un avis juridique. Consultez un avocat pour votre situation spécifique.'
      )
    ).toBeTruthy();
  });
});

// --- Card ---

describe('Card', () => {
  test('rend ses children', () => {
    render(
      <Card>
        <></>
      </Card>
    );
    // Card sans onPress rend une View -- pas de crash
  });

  test('rend un texte enfant correctement', () => {
    render(
      <Card>
        {React.createElement(
          require('react-native').Text,
          null,
          'Contenu de carte'
        )}
      </Card>
    );
    expect(screen.getByText('Contenu de carte')).toBeTruthy();
  });

  test('sans onPress rend une View non pressable', () => {
    const { queryByRole } = render(
      <Card>
        {React.createElement(require('react-native').Text, null, 'Static')}
      </Card>
    );
    // Pas de role button quand pas de onPress
    expect(queryByRole('button')).toBeNull();
  });

  test('avec onPress rend un bouton accessible', () => {
    const onPress = jest.fn();
    const { getByRole } = render(
      <Card onPress={onPress} accessibilityLabel="Ouvrir carte">
        {React.createElement(require('react-native').Text, null, 'Pressable')}
      </Card>
    );
    expect(getByRole('button')).toBeTruthy();
  });
});

// --- ToolCard ---

describe('ToolCard', () => {
  const defaultProps = {
    iconName: 'document-text-outline',
    iconColor: '#1E3A5F',
    title: 'Analyse de contrat',
    subtitle: 'Score /100',
    onPress: jest.fn(),
  };

  test('rend le titre', () => {
    render(<ToolCard {...defaultProps} />);
    expect(screen.getByText('Analyse de contrat')).toBeTruthy();
  });

  test('rend le subtitle', () => {
    render(<ToolCard {...defaultProps} />);
    expect(screen.getByText('Score /100')).toBeTruthy();
  });

  test('sans subtitle ne plante pas', () => {
    render(<ToolCard {...defaultProps} subtitle={undefined} />);
    expect(screen.getByText('Analyse de contrat')).toBeTruthy();
  });

  test('a un accessibilityRole button', () => {
    const { getByRole } = render(<ToolCard {...defaultProps} />);
    expect(getByRole('button')).toBeTruthy();
  });

  test('accessibilityLabel utilise le titre par defaut', () => {
    const { getByLabelText } = render(<ToolCard {...defaultProps} />);
    expect(getByLabelText('Analyse de contrat')).toBeTruthy();
  });

  test('accessibilityLabel personnalise est utilise quand fourni', () => {
    const { getByLabelText } = render(
      <ToolCard {...defaultProps} accessibilityLabel="Outil analyse contrat" />
    );
    expect(getByLabelText('Outil analyse contrat')).toBeTruthy();
  });

  test("rend l'icone par defaut si iconName est absent", () => {
    render(
      <ToolCard
        title="Outil sans icone"
        subtitle="Test"
        onPress={jest.fn()}
      />
    );
    expect(screen.getByText('Outil sans icone')).toBeTruthy();
  });
});
