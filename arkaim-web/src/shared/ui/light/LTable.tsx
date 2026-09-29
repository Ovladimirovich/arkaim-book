'use client';

import React, { useState, useMemo } from 'react';

interface Column {
  title?: React.ReactNode;
  dataIndex?: string;
  key?: string;
  render?: (value: unknown, record: unknown, index: number) => React.ReactNode;
  width?: number | string;
  sorter?: (a: unknown, b: unknown) => number;
}

interface LTableProps {
  columns: Column[];
  dataSource: unknown[];
  rowKey?: string | ((record: unknown) => string);
  size?: 'small' | 'middle' | 'large';
  pagination?: { pageSize?: number } | false;
  loading?: boolean;
  style?: React.CSSProperties;
  className?: string;
}

const CELL_PADDING = { small: 8, middle: 12, large: 16 };
const FONT_SIZE = { small: 12, middle: 14, large: 16 };

export function LTable({ columns, dataSource, rowKey, size = 'small', pagination, loading, style, className }: LTableProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const pageSize = pagination === false ? dataSource.length : (pagination?.pageSize || 10);
  const totalPages = Math.max(1, Math.ceil(dataSource.length / pageSize));

  const sorted = useMemo(() => {
    if (!sortKey) return dataSource;
    const col = columns.find(c => c.key === sortKey || c.dataIndex === sortKey);
    if (!col?.sorter) return dataSource;
    return [...dataSource].sort((a, b) => {
      const result = col.sorter!(a, b);
      return sortDir === 'asc' ? result : -result;
    });
  }, [dataSource, sortKey, sortDir, columns]);

  const pageData = useMemo(() => {
    if (pagination === false) return sorted;
    const start = (currentPage - 1) * pageSize;
    return sorted.slice(start, start + pageSize);
  }, [sorted, currentPage, pageSize, pagination]);

  const getRowKey = (record: unknown, idx: number): string => {
    if (typeof rowKey === 'function') return rowKey(record);
    if (typeof rowKey === 'string') return String((record as Record<string, unknown>)[rowKey] ?? idx);
    return String(idx);
  };

  const handleSort = (key: string) => {
    if (sortKey === key) {
      if (sortDir === 'asc') setSortDir('desc');
      else { setSortKey(null); setSortDir('asc'); }
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
    setCurrentPage(1);
  };

  const pad = CELL_PADDING[size];
  const fontSize = FONT_SIZE[size];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 24, color: 'var(--foreground)', opacity: 0.45, fontSize }}>
        Загрузка...
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'auto', ...style }} className={className}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize }}>
        <thead>
          <tr style={{ borderBottom: '2px solid var(--divider-color)' }}>
            {columns.map((col, i) => (
              <th
                key={col.key || String(i)}
                style={{
                  padding: pad,
                  textAlign: 'left',
                  fontWeight: 600,
                  color: 'var(--foreground)',
                  whiteSpace: 'nowrap',
                  width: col.width,
                  cursor: col.sorter ? 'pointer' : undefined,
                  userSelect: col.sorter ? 'none' : undefined,
                }}
                onClick={() => col.sorter && col.key && handleSort(col.key)}
              >
                {col.title}
                {col.sorter && col.key && sortKey === col.key && (
                  <span style={{ marginLeft: 4, fontSize: 10 }}>{sortDir === 'asc' ? '▲' : '▼'}</span>
                )}
                {col.sorter && (!col.key || sortKey !== col.key) && (
                  <span style={{ marginLeft: 4, fontSize: 10, opacity: 0.3 }}>⇅</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {pageData.length === 0 ? (
            <tr>
              <td colSpan={columns.length} style={{ padding: 24, textAlign: 'center', color: 'var(--foreground)', opacity: 0.45 }}>
                Нет данных
              </td>
            </tr>
          ) : (
            pageData.map((record, idx) => (
              <tr
                key={getRowKey(record, idx)}
                style={{ borderBottom: '1px solid var(--divider-color)', transition: 'background 0.15s' }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = 'color-mix(in srgb, var(--foreground) 5%, transparent)'; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >
                {columns.map((col, ci) => {
                  const value = col.dataIndex ? (record as Record<string, unknown>)[col.dataIndex] : undefined;
                  const cellContent = col.render ? col.render(value, record, idx) : (value != null ? String(value) : '—');
                  return (
                    <td key={col.key || String(ci)} style={{ padding: pad }}>
                      {cellContent}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
      {pagination !== false && totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 4, padding: '8px 0', fontSize }}>
          <button
            disabled={currentPage <= 1}
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            style={pageBtnStyle(currentPage <= 1)}
          >
            ‹
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
            <button
              key={p}
              onClick={() => setCurrentPage(p)}
              style={{
                ...pageBtnStyle(false),
                background: p === currentPage ? '#1677ff' : 'transparent',
                color: p === currentPage ? '#fff' : 'var(--foreground)',
                fontWeight: p === currentPage ? 600 : 400,
              }}
            >
              {p}
            </button>
          ))}
          <button
            disabled={currentPage >= totalPages}
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            style={pageBtnStyle(currentPage >= totalPages)}
          >
            ›
          </button>
        </div>
      )}
    </div>
  );
}

function pageBtnStyle(disabled: boolean): React.CSSProperties {
  return {
    border: '1px solid var(--input-border)',
    borderRadius: 4,
    padding: '2px 8px',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.4 : 1,
    fontSize: 12,
    lineHeight: '22px',
    background: 'transparent',
    color: 'var(--foreground)',
  };
}