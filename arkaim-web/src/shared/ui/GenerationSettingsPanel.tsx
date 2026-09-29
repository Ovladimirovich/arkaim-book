'use client';

import React from 'react';
import { Card, Select, Input, Space, Typography, Button, Collapse } from 'antd';
import { SettingOutlined, ReloadOutlined } from '@ant-design/icons';
import { useGenerationSettings, Provider, Quality } from '../contexts/GenerationSettingsContext';

const { TextArea } = Input;
const { Text } = Typography;

const STYLE_OPTIONS = [
  { value: 'cinematic_fantasy', label: 'Cinematic Fantasy' },
  { value: 'realistic', label: 'Realistic' },
  { value: 'watercolor', label: 'Watercolor' },
  { value: 'dark_gothic', label: 'Dark Gothic' },
  { value: 'ethereal', label: 'Ethereal' },
  { value: 'oil_painting', label: 'Oil Painting' },
];

const ALL_MOODS = [
  {
    label: 'Базовые',
    options: [
      { value: 'neutral', label: 'Нейтральная' },
      { value: 'warm_intimate', label: 'Тёплая/интимная' },
      { value: 'melancholic_dark', label: 'Меланхоличная/тёмная' },
      { value: 'hopeful_golden', label: 'Золотая/надежда' },
      { value: 'dark_mystical', label: 'Мистическая/тёмная' },
      { value: 'dramatic_contrast', label: 'Драматичный контраст' },
      { value: 'ethereal_light', label: 'Эфирный свет' },
      { value: 'sepia_flashback', label: 'Сепия/воспоминание' },
      { value: 'conflict', label: 'Конфликт' },
      { value: 'bright_warm', label: 'Яркая/тёплая' },
    ],
  },
  {
    label: 'Расширенные',
    options: [
      { value: 'ceremonial_warm', label: 'Церемониальная' },
      { value: 'sacred_glow', label: 'Священное сияние' },
      { value: 'melancholic_hopeful', label: 'Меланхолия/надежда' },
      { value: 'calm_acceptance', label: 'Спокойное приятие' },
      { value: 'duality_contrast', label: 'Двойственность' },
      { value: 'progressive_light', label: 'Прогрессивный свет' },
      { value: 'warm_devotion', label: 'Тёплая преданность' },
      { value: 'epic_reveal', label: 'Эпическое открытие' },
      { value: 'harmonious_blend', label: 'Гармоничное слияние' },
      { value: 'metamorphosis', label: 'Метаморфоза' },
    ],
  },
];

const SIZE_OPTIONS = [
  { value: '1024x1024', label: '1024×1024 (1:1)' },
  { value: '512x512', label: '512×512 (1:1)' },
  { value: '768x768', label: '768×768 (1:1)' },
  { value: '1024x576', label: '1024×576 (16:9)' },
  { value: '768x432', label: '768×432 (16:9)' },
];

const QUALITY_OPTIONS: { value: Quality; label: string }[] = [
  { value: 'draft', label: 'Draft' },
  { value: 'standard', label: 'Standard' },
  { value: 'high', label: 'High' },
  { value: 'ultra', label: 'Ultra' },
];

const PROVIDER_OPTIONS: { value: Provider; label: string }[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'comfyui', label: 'ComfyUI' },
  { value: 'mock', label: 'Mock' },
];

interface GenerationSettingsPanelProps {
  compact?: boolean;
}

export function GenerationSettingsPanel({ compact = false }: GenerationSettingsPanelProps) {
  const settings = useGenerationSettings();

  return (
    <Card
      size={compact ? 'small' : 'default'}
      title={<Space><SettingOutlined /> Настройки генерации</Space>}
      extra={
        <Button size="small" icon={<ReloadOutlined />} onClick={settings.resetSettings}>
          Сбросить
        </Button>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <Space wrap>
          <div>
            <Text type="secondary" style={{ fontSize: 11 }}>Провайдер</Text>
            <Select
              value={settings.provider}
              onChange={(value) => settings.updateSettings({ provider: value })}
              options={PROVIDER_OPTIONS}
              style={{ width: 120 }}
              size={compact ? 'small' : 'middle'}
            />
          </div>

          <div>
            <Text type="secondary" style={{ fontSize: 11 }}>Стиль</Text>
            <Select
              value={settings.style}
              onChange={(value) => settings.updateSettings({ style: value })}
              options={STYLE_OPTIONS}
              style={{ width: 140 }}
              size={compact ? 'small' : 'middle'}
            />
          </div>

          <div>
            <Text type="secondary" style={{ fontSize: 11 }}>Настроение</Text>
            <Select
              value={settings.mood}
              onChange={(value) => settings.updateSettings({ mood: value })}
              options={ALL_MOODS}
              style={{ width: 200 }}
              size={compact ? 'small' : 'middle'}
            />
          </div>

          <div>
            <Text type="secondary" style={{ fontSize: 11 }}>Качество</Text>
            <Select
              value={settings.quality}
              onChange={(value) => settings.updateSettings({ quality: value })}
              options={QUALITY_OPTIONS}
              style={{ width: 100 }}
              size={compact ? 'small' : 'middle'}
            />
          </div>

          <div>
            <Text type="secondary" style={{ fontSize: 11 }}>Размер</Text>
            <Select
              value={settings.size}
              onChange={(value) => settings.updateSettings({ size: value })}
              options={SIZE_OPTIONS}
              style={{ width: 140 }}
              size={compact ? 'small' : 'middle'}
            />
          </div>
        </Space>

        <Collapse size="small" ghost>
          <Collapse.Panel header="Negative Prompt" key="negative">
            <TextArea
              value={settings.negativePrompt}
              onChange={(e) => settings.updateSettings({ negativePrompt: e.target.value })}
              placeholder="blurry, cartoon, low quality..."
              rows={2}
              style={{ fontSize: 12 }}
            />
          </Collapse.Panel>
        </Collapse>
      </Space>
    </Card>
  );
}
