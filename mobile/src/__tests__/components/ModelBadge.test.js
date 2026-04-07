/**
 * Tests — ModelBadge
 * Composant critique utilisé dans 7 écrans Lexavo.
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import ModelBadge from '../../components/ModelBadge';

describe('ModelBadge', () => {

  // ── Détection du modèle ──────────────────────────────────────────────────

  describe('détection Haiku', () => {
    it('affiche "Haiku" pour "claude-haiku-4-5"', () => {
      const { getByText } = render(<ModelBadge model="claude-haiku-4-5" />);
      expect(getByText('Haiku')).toBeTruthy();
    });

    it('affiche la description correcte pour Haiku', () => {
      const { getByText } = render(<ModelBadge model="claude-haiku-4-5" />);
      expect(getByText('Réponse rapide')).toBeTruthy();
    });

    it('affiche "⚡" pour Haiku', () => {
      const { getByText } = render(<ModelBadge model="claude-haiku-4-5-20251001" />);
      expect(getByText('⚡')).toBeTruthy();
    });

    it('est insensible à la casse pour haiku', () => {
      const { getByText } = render(<ModelBadge model="CLAUDE-HAIKU" />);
      expect(getByText('Haiku')).toBeTruthy();
    });
  });

  describe('détection Sonnet', () => {
    it('affiche "Sonnet" pour "claude-sonnet-4-6"', () => {
      const { getByText } = render(<ModelBadge model="claude-sonnet-4-6" />);
      expect(getByText('Sonnet')).toBeTruthy();
    });

    it('affiche la description correcte pour Sonnet', () => {
      const { getByText } = render(<ModelBadge model="claude-sonnet-4-6" />);
      expect(getByText('Analyse avancée')).toBeTruthy();
    });

    it('affiche "🔵" pour Sonnet', () => {
      const { getByText } = render(<ModelBadge model="claude-sonnet-4-6" />);
      expect(getByText('🔵')).toBeTruthy();
    });
  });

  describe('détection Opus', () => {
    it('affiche "Opus" pour "claude-opus-4-6"', () => {
      const { getByText } = render(<ModelBadge model="claude-opus-4-6" />);
      expect(getByText('Opus')).toBeTruthy();
    });

    it('affiche la description correcte pour Opus', () => {
      const { getByText } = render(<ModelBadge model="claude-opus-4-6" />);
      expect(getByText('Cas complexe')).toBeTruthy();
    });

    it('affiche "💎" pour Opus', () => {
      const { getByText } = render(<ModelBadge model="claude-opus-4-6" />);
      expect(getByText('💎')).toBeTruthy();
    });
  });

  // ── Cas null/undefined/inconnu ───────────────────────────────────────────

  describe('modèle absent ou inconnu', () => {
    it('retourne null pour model=null', () => {
      const { toJSON } = render(<ModelBadge model={null} />);
      expect(toJSON()).toBeNull();
    });

    it('retourne null pour model=undefined', () => {
      const { toJSON } = render(<ModelBadge model={undefined} />);
      expect(toJSON()).toBeNull();
    });

    it('retourne null pour model=""', () => {
      const { toJSON } = render(<ModelBadge model="" />);
      expect(toJSON()).toBeNull();
    });

    it('retourne null pour un modèle non reconnu', () => {
      const { toJSON } = render(<ModelBadge model="gpt-4-turbo" />);
      expect(toJSON()).toBeNull();
    });

    it('retourne null pour "gemini-pro"', () => {
      const { toJSON } = render(<ModelBadge model="gemini-pro" />);
      expect(toJSON()).toBeNull();
    });
  });

  // ── Style prop ───────────────────────────────────────────────────────────

  describe('style prop', () => {
    it('accepte un style personnalisé sans crash', () => {
      expect(() =>
        render(<ModelBadge model="claude-sonnet-4-6" style={{ marginTop: 10 }} />)
      ).not.toThrow();
    });

    it('rend correctement avec style={{ alignSelf: "center", marginBottom: 0 }}', () => {
      const { getByText } = render(
        <ModelBadge model="claude-sonnet-4-6" style={{ alignSelf: 'center', marginBottom: 0 }} />
      );
      expect(getByText('Sonnet')).toBeTruthy();
    });
  });

  // ── Séparateur ───────────────────────────────────────────────────────────

  it('affiche le séparateur "·"', () => {
    const { getByText } = render(<ModelBadge model="claude-haiku-4-5" />);
    expect(getByText('·')).toBeTruthy();
  });
});
