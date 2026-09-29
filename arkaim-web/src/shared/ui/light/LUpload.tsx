'use client';

import React, { useCallback, useState, useRef } from 'react';
import { InboxOutlined, FileTextOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { LButton } from './LButton';

interface UploadFile {
  file: File;
  name: string;
  size: number;
  status?: 'uploading' | 'done' | 'error';
}

interface LUploadProps {
  accept?: string;
  maxCount?: number;
  beforeUpload?: (file: File) => boolean;
  showUploadList?: boolean;
  disabled?: boolean;
  children?: React.ReactNode;
  onRemove?: (file: UploadFile) => void;
  style?: React.CSSProperties;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export function LUpload({
  accept, maxCount, beforeUpload, showUploadList = true,
  disabled, children, onRemove, style,
}: LUploadProps) {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFile = useCallback((file: File) => {
    if (beforeUpload && !beforeUpload(file)) return;
    if (maxCount && files.length >= maxCount) return;
    setFiles(prev => [...prev, { file, name: file.name, size: file.size }]);
  }, [beforeUpload, maxCount, files.length]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) addFile(droppedFile);
  }, [addFile]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) addFile(selectedFile);
    e.target.value = '';
  }, [addFile]);

  const removeFile = useCallback((index: number) => {
    const removed = files[index];
    setFiles(prev => prev.filter((_, i) => i !== index));
    onRemove?.(removed);
  }, [files, onRemove]);

  return (
    <div style={style}>
      <div
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? '#1677ff' : '#d9d9d9'}`,
          borderRadius: 8,
          padding: '24px 16px',
          textAlign: 'center',
          cursor: disabled ? 'not-allowed' : 'pointer',
          background: dragOver ? '#f0f5ff' : 'var(--surface-bg)',
          transition: 'all 0.2s',
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleInputChange}
          style={{ display: 'none' }}
          disabled={disabled}
        />
        {children || (
          <>
            <InboxOutlined style={{ fontSize: 40, color: dragOver ? '#1677ff' : '#999' }} />
            <p style={{ margin: '8px 0 0', color: '#333', fontWeight: 500 }}>Нажмите или перетащите файл</p>
            <p style={{ margin: '4px 0 0', fontSize: 12, color: '#999' }}>Поддерживаются: .txt, .md, .json, .pdf, .doc, .docx (макс. 50MB)</p>
          </>
        )}
      </div>

      {showUploadList && files.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {files.map((f, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', borderBottom: '1px solid #f5f5f5' }}>
              <FileTextOutlined style={{ color: '#1677ff' }} />
              <span style={{ flex: 1, fontSize: 13 }}>{f.name}</span>
              <span style={{ fontSize: 11, color: '#999' }}>{formatSize(f.size)}</span>
              <LButton size="small" onClick={() => removeFile(i)} icon={<CloseCircleOutlined />} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}