'use client';

import React from 'react';

interface LInputProps {
  value?: string;
  defaultValue?: string;
  id?: string;
  placeholder?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onPressEnter?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
  addonBefore?: React.ReactNode;
  allowClear?: boolean;
  disabled?: boolean;
  readOnly?: boolean;
  size?: 'small' | 'middle' | 'large';
  type?: string;
  style?: React.CSSProperties;
  className?: string;
  onClick?: (e: React.MouseEvent) => void;
}

const SIZES = { small: 24, middle: 32, large: 40 };

export function LInput({
  value, defaultValue, id, placeholder, onChange, onPressEnter,
  prefix, suffix, addonBefore, allowClear, disabled, readOnly, size = 'middle', type = 'text',
  style, className, onClick,
}: LInputProps) {
  const height = SIZES[size];
  const fontSize = size === 'small' ? 12 : 14;

  const hasValue = value !== undefined && value !== '';
  const allowClearActive = allowClear && hasValue;

  const clearHandler = (e: React.MouseEvent) => {
    e.stopPropagation();
    const syntheticEvent = {
      target: { value: '' },
      currentTarget: { value: '' },
    } as React.ChangeEvent<HTMLInputElement>;
    onChange?.(syntheticEvent);
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    height,
    padding: `0 ${suffix ? 32 : 12}px`,
    paddingLeft: prefix ? 36 : addonBefore ? 0 : 12,
    fontSize,
    border: '1px solid var(--input-border)',
    borderRadius: addonBefore ? '0 6px 6px 0' : 6,
    outline: 'none',
    transition: 'border-color 0.2s, box-shadow 0.2s',
    background: disabled ? 'var(--divider-color)' : 'var(--input-bg)',
    color: disabled ? 'var(--foreground)' : 'var(--foreground)',
    opacity: disabled ? 0.5 : 1,
    cursor: disabled ? 'not-allowed' : readOnly ? 'pointer' : 'text',
    boxSizing: 'border-box' as const,
    ...style,
  };

  const input = (
    <input
      type={type}
      id={id}
      value={value}
      defaultValue={defaultValue}
      placeholder={placeholder}
      onChange={onChange}
      onKeyDown={onPressEnter ? (e) => { if (e.key === 'Enter') onPressEnter(e); } : undefined}
      disabled={disabled}
      readOnly={readOnly}
      onClick={onClick}
      style={inputStyle}
    />
  );

  if (addonBefore) {
    return (
      <div style={{ display: 'inline-flex', width: style?.width || '100%', alignItems: 'center' }} className={className}>
        <span style={{ display: 'flex', alignItems: 'center', padding: `0 8px`, height, fontSize, background: 'var(--surface-bg)', border: '1px solid var(--input-border)', borderRight: 'none', borderRadius: '6px 0 0 6px', color: 'var(--foreground)', whiteSpace: 'nowrap' }}>{addonBefore}</span>
        <div style={{ position: 'relative', flex: 1 }}>
          {prefix && (
            <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--foreground)', opacity: 0.45, fontSize, display: 'flex', alignItems: 'center', zIndex: 1 }}>
              {prefix}
            </span>
          )}
          {input}
          {allowClearActive && !disabled && (
            <span onClick={clearHandler} style={{ cursor: 'pointer', lineHeight: 1, fontSize: 14, userSelect: 'none', color: 'var(--foreground)' }}>✕</span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', display: 'inline-block', width: style?.width || '100%' }} className={className}>
      {prefix && (
        <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--foreground)', opacity: 0.45, fontSize, display: 'flex', alignItems: 'center', zIndex: 1 }}>
          {prefix}
        </span>
      )}
      {input}
      {(allowClearActive || suffix) && (
        <span style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--foreground)', opacity: 0.45, fontSize, display: 'flex', alignItems: 'center', gap: 4 }}>
          {allowClearActive && !disabled && (
            <span onClick={clearHandler} style={{ cursor: 'pointer', lineHeight: 1, fontSize: 14, userSelect: 'none' }}>✕</span>
          )}
          {suffix}
        </span>
      )}
    </div>
  );
}

interface LTextAreaProps {
  value?: string;
  defaultValue?: string;
  placeholder?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onPressEnter?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  rows?: number;
  disabled?: boolean;
  autoSize?: { minRows?: number; maxRows?: number };
  style?: React.CSSProperties;
}

export const LTextArea = React.forwardRef<HTMLTextAreaElement, LTextAreaProps>(({ value, defaultValue, placeholder, onChange, onPressEnter, rows = 4, disabled, autoSize, style }, ref) => {
  const autoResize = React.useCallback(() => {
    const ta = ref && 'current' in ref ? (ref as React.RefObject<HTMLTextAreaElement | null>).current : null;
    if (!ta || !autoSize) return;
    ta.style.height = 'auto';
    const minH = (autoSize.minRows || 1) * 22;
    const maxH = (autoSize.maxRows || Infinity) * 22;
    ta.style.height = `${Math.max(minH, Math.min(ta.scrollHeight, maxH))}px`;
  }, [autoSize, ref]);

  React.useEffect(() => {
    autoResize();
  }, [value, autoResize]);

  const innerRef = React.useRef<HTMLTextAreaElement>(null);
  const resolvedRef = (ref || innerRef) as React.RefObject<HTMLTextAreaElement>;

  return (
    <textarea
      ref={resolvedRef}
      value={value}
      defaultValue={defaultValue}
      placeholder={placeholder}
      onChange={(e) => { onChange?.(e); autoResize(); }}
      onKeyDown={onPressEnter ? (e) => { if (e.key === 'Enter' && !e.shiftKey) onPressEnter(e); } : undefined}
      rows={rows}
      disabled={disabled}
      style={{
        width: '100%',
        padding: '8px 12px',
        fontSize: 14,
        border: '1px solid var(--input-border)',
        borderRadius: 6,
        outline: 'none',
        resize: autoSize ? 'none' : 'vertical',
        background: disabled ? 'var(--divider-color)' : 'var(--input-bg)',
        color: disabled ? 'var(--foreground)' : 'var(--foreground)',
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? 'not-allowed' : 'text',
        boxSizing: 'border-box' as const,
        overflow: autoSize ? 'hidden' : 'auto',
        ...style,
      }}
    />
  );
});

LTextArea.displayName = 'LTextArea';