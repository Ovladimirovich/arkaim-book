'use client';

import React from 'react';

interface LInputNumberProps {
  value?: number;
  defaultValue?: number;
  min?: number;
  max?: number;
  step?: number;
  onChange?: (value: number | null) => void;
  disabled?: boolean;
  style?: React.CSSProperties;
  size?: 'small' | 'middle' | 'large';
}

const SIZES = { small: 24, middle: 32, large: 40 };

export function LInputNumber({ value, defaultValue, min, max, step = 1, onChange, disabled, style, size = 'middle' }: LInputNumberProps) {
  const [internalValue, setInternalValue] = React.useState(defaultValue ?? min ?? 0);
  const currentValue = value ?? internalValue;
  const height = SIZES[size];

  const clamp = (v: number) => {
    let result = v;
    if (min !== undefined) result = Math.max(min, result);
    if (max !== undefined) result = Math.min(max, result);
    return result;
  };

  const setValue = (val: number) => {
    const clamped = clamp(val);
    const rounded = Math.round(clamped * 100) / 100;
    if (value === undefined) setInternalValue(rounded);
    onChange?.(rounded);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const parsed = parseFloat(e.target.value);
    if (isNaN(parsed)) {
      if (value === undefined) setInternalValue(min ?? 0);
      onChange?.(null);
      return;
    }
    setValue(parsed);
  };

  const btnStyle: React.CSSProperties = {
    width: height,
    height,
    border: '1px solid var(--input-border)',
    background: 'var(--surface-bg)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontSize: size === 'small' ? 12 : 14,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: disabled ? '#bfbfbf' : 'var(--foreground)',
    opacity: disabled ? 0.5 : 1,
  };

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', ...style }}>
      <button style={{ ...btnStyle, borderRadius: '6px 0 0 6px', borderRight: 'none' }} disabled={disabled} onClick={() => setValue(currentValue - step)}>−</button>
      <input
        type="number"
        value={currentValue}
        onChange={handleChange}
        disabled={disabled}
        min={min}
        max={max}
        step={step}
        style={{
          width: height * 2,
          height,
          border: '1px solid var(--input-border)',
          textAlign: 'center',
          fontSize: 14,
          outline: 'none',
          background: disabled ? '#f5f5f5' : 'var(--input-bg)',
          color: disabled ? '#bfbfbf' : 'var(--foreground)',
          MozAppearance: 'textfield',
        }}
      />
      <button style={{ ...btnStyle, borderRadius: '0 6px 6px 0', borderLeft: 'none' }} disabled={disabled} onClick={() => setValue(currentValue + step)}>+</button>
    </div>
  );
}