'use client';

import React from 'react';

interface LRadioGroupProps {
  value?: string;
  onChange?: (value: string) => void;
  children: React.ReactNode;
  style?: React.CSSProperties;
}

interface LRadioButtonProps {
  value: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}

const RadioGroupContext = React.createContext<{
  selectedValue?: string;
  onSelect: (value: string) => void;
}>({ selectedValue: undefined, onSelect: () => {} });

function LRadioButton({ value, children, style }: LRadioButtonProps) {
  const ctx = React.useContext(RadioGroupContext);
  const isSelected = ctx.selectedValue === value;

  return (
    <button
      type="button"
      onClick={() => ctx.onSelect(value)}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 16px',
        border: `1px solid ${isSelected ? '#1677ff' : '#d9d9d9'}`,
        borderRadius: 6,
        background: isSelected ? '#1677ff' : 'var(--surface-bg)',
        color: isSelected ? '#fff' : 'var(--foreground)',
        cursor: 'pointer',
        fontSize: 13,
        transition: 'all 0.2s',
        ...style,
      }}
    >
      {children}
    </button>
  );
}

export function LRadioGroup({ value, onChange, children, style }: LRadioGroupProps) {
  return (
    <RadioGroupContext.Provider value={{ selectedValue: value, onSelect: (v) => onChange?.(v) }}>
      <div style={{ display: 'inline-flex', gap: 4, ...style }}>
        {children}
      </div>
    </RadioGroupContext.Provider>
  );
}

const LRadio = Object.assign(LRadioGroup, { Button: LRadioButton });
export { LRadio };