'use client';

import React, { useState, useRef, useEffect } from 'react';

interface SelectOption {
  value: string;
  label: string;
}

interface LSelectProps {
  value?: string;
  defaultValue?: string;
  options: SelectOption[];
  onChange?: (value: string) => void;
  placeholder?: string;
  style?: React.CSSProperties;
  className?: string;
  disabled?: boolean;
}

export function LSelect({ value, defaultValue, options, onChange, placeholder, style, className, disabled }: LSelectProps) {
  const [open, setOpen] = useState(false);
  const [internalValue, setInternalValue] = useState<string | undefined>(defaultValue);
  const ref = useRef<HTMLDivElement>(null);
  const currentValue = value !== undefined ? value : internalValue;
  const selected = options.find(o => o.value === currentValue);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleSelect = (val: string) => {
    if (value === undefined) setInternalValue(val);
    onChange?.(val);
    setOpen(false);
  };

  return (
    <div ref={ref} style={{ position: 'relative', ...style }} className={className}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen(!open)}
        style={{
          width: '100%',
          height: 32,
          padding: '0 28px 0 12px',
          border: `1px solid ${open ? '#1677ff' : 'var(--input-border)'}`,
          borderRadius: 6,
          background: disabled ? 'var(--divider-color)' : 'var(--input-bg)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          textAlign: 'left',
          fontSize: 14,
          color: selected ? 'var(--foreground)' : 'var(--foreground)',
          opacity: selected ? 1 : 0.65,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {selected ? selected.label : placeholder || 'Выберите...'}
        </span>
        <span style={{
          borderLeft: '4px solid transparent',
          borderRight: '4px solid transparent',
          borderTop: '5px solid var(--foreground)',
          opacity: 0.45,
          transition: 'transform 0.2s',
          transform: open ? 'rotate(180deg)' : undefined,
        }} />
      </button>
      {open && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          marginTop: 4,
          background: 'var(--surface-bg)',
          border: '1px solid var(--input-border)',
          borderRadius: 6,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          zIndex: 1000,
          maxHeight: 200,
          overflowY: 'auto',
        }}>
          {options.map(opt => (
            <div
              key={opt.value}
              onClick={() => handleSelect(opt.value)}
              style={{
                padding: '8px 12px',
                cursor: 'pointer',
                fontSize: 14,
                color: opt.value === currentValue ? '#1677ff' : 'var(--foreground)',
                background: opt.value === currentValue ? 'var(--card-border)' : 'transparent',
                fontWeight: opt.value === currentValue ? 500 : 400,
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = 'var(--card-border)'; }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background =
                  opt.value === currentValue ? 'var(--card-border)' : 'transparent';
              }}
            >
              {opt.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}