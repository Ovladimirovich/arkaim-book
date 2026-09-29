'use client';

import React, { useState } from 'react';

interface TabItem {
  key: string;
  label: React.ReactNode;
  children: React.ReactNode;
}

interface LTabsProps {
  items: TabItem[];
  activeKey?: string;
  defaultActiveKey?: string;
  onChange?: (key: string) => void;
  style?: React.CSSProperties;
}

export function LTabs({ items, activeKey, defaultActiveKey, onChange, style }: LTabsProps) {
  const [internalKey, setInternalKey] = useState(defaultActiveKey || items[0]?.key || '');
  const currentKey = activeKey ?? internalKey;

  const handleChange = (key: string) => {
    if (activeKey === undefined) setInternalKey(key);
    onChange?.(key);
  };

  const activeTab = items.find(tab => tab.key === currentKey);

  return (
    <div style={style}>
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--card-border)', marginBottom: 16 }}>
        {items.map(tab => (
          <button
            key={tab.key}
            onClick={() => handleChange(tab.key)}
            style={{
              padding: '12px 16px',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: 14,
              color: currentKey === tab.key ? '#1677ff' : 'var(--foreground)',
              borderBottom: currentKey === tab.key ? '2px solid #1677ff' : '2px solid transparent',
              marginBottom: -1,
              fontWeight: currentKey === tab.key ? 500 : 400,
              opacity: 0.85,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {activeTab && <div key={currentKey}>{activeTab.children}</div>}
    </div>
  );
}