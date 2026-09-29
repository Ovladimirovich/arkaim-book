'use client';

import React from 'react';

interface LSwitchProps {
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
  checkedChildren?: React.ReactNode;
  unCheckedChildren?: React.ReactNode;
  style?: React.CSSProperties;
}

export function LSwitch({ checked, onChange, disabled, checkedChildren, unCheckedChildren, style }: LSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange?.(!checked)}
      style={{
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        width: checkedChildren || unCheckedChildren ? 56 : 40,
        height: 22,
        padding: 0,
        border: 'none',
        borderRadius: 11,
        background: checked ? '#1677ff' : '#d9d9d9',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'background 0.2s',
        ...style,
      }}
    >
      <span
        style={{
          position: 'absolute',
          left: checked ? (checkedChildren || unCheckedChildren ? 34 : 18) : 2,
          width: 18,
          height: 18,
          borderRadius: 9,
          background: 'var(--surface-bg)',
          boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
          transition: 'left 0.2s',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      />
      {(checkedChildren || unCheckedChildren) && (
        <span style={{
          fontSize: 10,
          color: checked ? '#fff' : '#999',
          marginLeft: checked ? 6 : 22,
          marginRight: checked ? 22 : 6,
          lineHeight: '22px',
        }}>
          {checked ? checkedChildren : unCheckedChildren}
        </span>
      )}
    </button>
  );
}