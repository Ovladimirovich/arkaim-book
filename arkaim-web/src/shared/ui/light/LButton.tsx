'use client';

import React from 'react';

interface LButtonProps {
  children?: React.ReactNode;
  type?: 'primary' | 'default' | 'dashed' | 'text' | 'link';
  size?: 'small' | 'middle' | 'large';
  danger?: boolean;
  ghost?: boolean;
  block?: boolean;
  loading?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  onClick?: (e: React.MouseEvent) => void;
  htmlType?: 'button' | 'submit' | 'reset';
  href?: string;
  target?: string;
  style?: React.CSSProperties;
  className?: string;
}

const SIZES = { small: 24, middle: 32, large: 40 };

export function LButton({
  children, type = 'default', size = 'middle', danger, loading,
  disabled, block, icon, onClick, htmlType = 'button', href, target,
  style, className,
}: LButtonProps) {
  const height = SIZES[size];
  const fontSize = size === 'small' ? 12 : 14;

  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    height,
    padding: `0 ${height === 24 ? 7 : height === 40 ? 15 : 11}px`,
    fontSize,
    borderRadius: 6,
    border: '1px solid var(--input-border)',
    background: 'var(--surface-bg)',
    color: danger ? '#ff4d4f' : 'var(--foreground)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    transition: 'all 0.2s',
    whiteSpace: 'nowrap',
    textDecoration: 'none',
    lineHeight: 1,
    width: block ? '100%' : undefined,
    ...style,
  };

  const variants: Record<string, React.CSSProperties> = {
    primary: { background: danger ? '#ff4d4f' : '#1677ff', color: '#fff', borderColor: danger ? '#ff4d4f' : '#1677ff' },
    dashed: { borderStyle: 'dashed' },
    text: { border: 'none', background: 'transparent' },
    link: { border: 'none', background: 'transparent', color: danger ? '#ff4d4f' : '#1677ff' },
  };

  const finalStyle = { ...baseStyle, ...variants[type] };

  const content = (
    <>
      {loading && <span style={{ animation: 'lspin 0.8s linear infinite', display: 'inline-block', width: 14, height: 14, border: '2px solid currentColor', borderTopColor: 'transparent', borderRadius: '50%' }} />}
      {!loading && icon}
      {children}
    </>
  );

  if (href) {
    return <a href={href} target={target} style={finalStyle} className={className}>{content}</a>;
  }

  return <button type={htmlType} disabled={disabled} onClick={onClick} style={finalStyle} className={className}>{content}</button>;
}
