'use client';

import React, { useRef, useCallback } from 'react';

interface LSliderProps {
  min?: number;
  max?: number;
  step?: number;
  value?: number;
  defaultValue?: number;
  onChange?: (value: number) => void;
  style?: React.CSSProperties;
  disabled?: boolean;
}

export function LSlider({ min = 0, max = 100, step = 1, value, defaultValue, onChange, style, disabled }: LSliderProps) {
  const [internalValue, setInternalValue] = React.useState(defaultValue ?? min);
  const currentValue = value ?? internalValue;
  const railRef = useRef<HTMLDivElement>(null);

  const percent = ((currentValue - min) / (max - min)) * 100;

  const setValue = useCallback((val: number) => {
    const clamped = Math.max(min, Math.min(max, val));
    const stepped = Math.round((clamped - min) / step) * step + min;
    const rounded = Math.round(stepped * 100) / 100;
    if (value === undefined) setInternalValue(rounded);
    onChange?.(rounded);
  }, [min, max, step, value, onChange]);

  const handlePointerDown = (e: React.PointerEvent) => {
    if (disabled) return;
    const rail = railRef.current;
    if (!rail) return;
    const rect = rail.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    setValue(min + pct * (max - min));

    const handleMove = (ev: PointerEvent) => {
      const r = rail.getBoundingClientRect();
      const p = Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width));
      setValue(min + p * (max - min));
    };
    const handleUp = () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };
    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
  };

  return (
    <div
      style={{ position: 'relative', height: 24, display: 'flex', alignItems: 'center', cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1, userSelect: 'none', touchAction: 'none', ...style }}
      onPointerDown={handlePointerDown}
    >
      <div ref={railRef} style={{ flex: 1, height: 4, background: 'var(--divider-color)', borderRadius: 2, position: 'relative' }}>
        <div style={{ position: 'absolute', top: 0, left: 0, height: '100%', width: `${percent}%`, background: '#1677ff', borderRadius: 2 }} />
        <div
          style={{
            position: 'absolute', top: '50%', left: `${percent}%`,
            width: 14, height: 14, borderRadius: '50%',
            background: 'var(--surface-bg)', border: '2px solid #1677ff',
            transform: 'translate(-50%, -50%)',
            boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
          }}
        />
      </div>
    </div>
  );
}