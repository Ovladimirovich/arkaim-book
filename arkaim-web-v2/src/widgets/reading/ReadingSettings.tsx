/**
 * widgets/reading/ReadingSettings.tsx — panel nastavok chteniya.
 */
'use client';

import { useMemo } from 'react';
import {
  type ReadingSettings,
  type FontSize,
  paragraphSpacingPx,
} from '@/entities/reader/types';

interface Props {
  settings: ReadingSettings;
  effectiveTheme: 'light' | 'dark';
  onChange: <K extends keyof ReadingSettings>(key: K, value: ReadingSettings[K]) => void;
  onReset: () => void;
  onClose: () => void;
}

const FONT_SIZES: FontSize[] = [15, 16, 17, 18, 19, 20];
const LINE_HEIGHTS: ReadingSettings['lineHeight'][] = [1.6, 1.7, 1.8, 1.9, 2.0];
const SPACINGS: ReadingSettings['paragraphSpacing'][] = ['compact', 'normal', 'relaxed'];
const SPACING_LABELS: Record<string, string> = {
  compact: 'Компактный',
  normal: 'Обычный',
  relaxed: 'Расслабленный',
};

export function ReadingSettings({ settings, effectiveTheme, onChange, onReset, onClose }: Props) {
  const colWidthPxValue = useMemo(() => {
    const map: Record<FontSize, number> = {
      15: 540, 16: 576, 17: 612, 18: 648, 19: 684, 20: 720,
    };
    return map[settings.fontSize] ?? 612;
  }, [settings.fontSize]);

  return (
    <div
      role="dialog"
      aria-label="Настройки чтения"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.4)',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--reading-surface)',
          border: '1px solid var(--reading-border)',
          borderRadius: 12,
          padding: 24,
          width: '100%',
          maxWidth: 420,
          margin: 16,
          boxShadow: 'var(--reading-shadow-md)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 24,
          }}
        >
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Настройки чтения</h2>
          <button
            onClick={onClose}
            aria-label="Закрыть"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: 20,
              color: 'var(--reading-text-secondary)',
              padding: '4px 8px',
              borderRadius: 4,
            }}
          >
            ×
          </button>
        </div>

        {/* Font size */}
        <SettingSection label="Размер шрифта">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {FONT_SIZES.map((size) => (
              <button
                key={size}
                onClick={() => onChange('fontSize', size)}
                style={{
                  padding: '6px 12px',
                  border: `1px solid ${settings.fontSize === size ? 'var(--reading-accent)' : 'var(--reading-border)'}`,
                  borderRadius: 6,
                  background: settings.fontSize === size ? 'var(--reading-active)' : 'transparent',
                  color: settings.fontSize === size ? 'var(--reading-accent)' : 'var(--reading-text)',
                  cursor: 'pointer',
                  fontSize: size,
                  fontFamily: 'Georgia, serif',
                  lineHeight: 1.4,
                }}
              >
                {size}px
              </button>
            ))}
          </div>
        </SettingSection>

        {/* Line height */}
        <SettingSection label="Межстрочный интервал">
          <div style={{ display: 'flex', gap: 8 }}>
            {LINE_HEIGHTS.map((lh) => (
              <button
                key={lh}
                onClick={() => onChange('lineHeight', lh)}
                style={{
                  padding: '6px 12px',
                  border: `1px solid ${settings.lineHeight === lh ? 'var(--reading-accent)' : 'var(--reading-border)'}`,
                  borderRadius: 6,
                  background: settings.lineHeight === lh ? 'var(--reading-active)' : 'transparent',
                  color: settings.lineHeight === lh ? 'var(--reading-accent)' : 'var(--reading-text)',
                  cursor: 'pointer',
                  fontSize: 13,
                }}
              >
                {lh}
              </button>
            ))}
          </div>
        </SettingSection>

        {/* Paragraph spacing */}
        <SettingSection label="Интервал между абзацами">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {SPACINGS.map((sp) => (
              <button
                key={sp}
                onClick={() => onChange('paragraphSpacing', sp)}
                style={{
                  padding: '6px 12px',
                  border: `1px solid ${settings.paragraphSpacing === sp ? 'var(--reading-accent)' : 'var(--reading-border)'}`,
                  borderRadius: 6,
                  background: settings.paragraphSpacing === sp ? 'var(--reading-active)' : 'transparent',
                  color: settings.paragraphSpacing === sp ? 'var(--reading-accent)' : 'var(--reading-text)',
                  cursor: 'pointer',
                  fontSize: 13,
                }}
              >
                {SPACING_LABELS[sp]}
              </button>
            ))}
          </div>
        </SettingSection>

        {/* Theme */}
        <SettingSection label="Тема">
          <div style={{ display: 'flex', gap: 8 }}>
            {(['light', 'dark', 'auto'] as const).map((t) => (
              <button
                key={t}
                onClick={() => onChange('theme', t)}
                style={{
                  padding: '6px 12px',
                  border: `1px solid ${settings.theme === t ? 'var(--reading-accent)' : 'var(--reading-border)'}`,
                  borderRadius: 6,
                  background: settings.theme === t ? 'var(--reading-active)' : 'transparent',
                  color: settings.theme === t ? 'var(--reading-accent)' : 'var(--reading-text)',
                  cursor: 'pointer',
                  fontSize: 13,
                }}
              >
                {t === 'light' ? 'Светлая' : t === 'dark' ? 'Тёмная' : 'Авто'}
              </button>
            ))}
          </div>
        </SettingSection>

        {/* Preview */}
        <SettingSection label="Предпросмотр">
          <div
            data-reading-theme={effectiveTheme}
            style={{
              fontFamily: 'Georgia, serif',
              fontSize: settings.fontSize,
              lineHeight: settings.lineHeight,
              padding: 16,
              background: effectiveTheme === 'dark' ? '#1a1a1a' : '#faf9f6',
              color: effectiveTheme === 'dark' ? '#e5e5e5' : '#1a1a1a',
              border: '1px solid var(--reading-border)',
              borderRadius: 8,
              maxWidth: colWidthPxValue,
            }}
          >
            <p
              style={{
                textIndent: '2em',
                marginBottom: `${paragraphSpacingPx(settings.paragraphSpacing)}em`,
              }}
            >
              Это предпросмотр текста с текущими настройками. Шрифт Georgia создаёт ощущение
              настоящей книги, а не веб-страницы.
            </p>
            <p
              style={{
                textIndent: '2em',
                marginBottom: `${paragraphSpacingPx(settings.paragraphSpacing)}em`,
              }}
            >
              Ширина колонки настроена оптимально для комфортного чтения — примерно 68 символов
              в строке при данном размере шрифта.
            </p>
          </div>
        </SettingSection>

        {/* Reset */}
        <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={onReset}
            style={{
              padding: '6px 16px',
              border: '1px solid var(--reading-border)',
              borderRadius: 6,
              background: 'transparent',
              color: 'var(--reading-text-secondary)',
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            Сбросить
          </button>
        </div>
      </div>
    </div>
  );
}

function SettingSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div
        style={{
          fontSize: 12,
          color: 'var(--reading-text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          marginBottom: 10,
          fontWeight: 600,
        }}
      >
        {label}
      </div>
      {children}
    </div>
  );
}
