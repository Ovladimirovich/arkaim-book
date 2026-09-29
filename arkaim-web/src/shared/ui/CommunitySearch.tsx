'use client';

import { useState } from 'react';
import { Input, Tabs, List, Card, Typography, Space, Tag, Button, Empty, Spin } from 'antd';
import { SearchOutlined, LikeOutlined, UserOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';

const { Text, Paragraph } = Typography;

type Interpretation = {
  id: string;
  reader_name: string;
  text: string;
  themes: string[];
  characters: string[];
  created_at: string;
  likes: number;
};

type Artifact = {
  id: string;
  reader_name: string;
  title: string;
  description: string;
  category: string;
  connection_to_book: string;
  related_themes: string[];
  location: string;
  created_at: string;
  likes: number;
};

type SearchResult = {
  interpretations: Interpretation[];
  artifacts: Artifact[];
  total: number;
};

export function CommunitySearch() {
  const [query, setQuery] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['community-search', searchQuery],
    queryFn: () => api.get<SearchResult>(`/book/community/search?q=${encodeURIComponent(searchQuery)}`),
    enabled: searchQuery.length >= 2,
  });

  const handleSearch = () => {
    if (query.trim().length >= 2) {
      setSearchQuery(query.trim());
    }
  };

  const interpretations = data?.interpretations || [];
  const artifacts = data?.artifacts || [];

  return (
    <div>
      <Input.Search
        value={query}
        onChange={e => setQuery(e.target.value)}
        onSearch={handleSearch}
        placeholder="Поиск по интерпретациям и артефактам..."
        enterButton={<><SearchOutlined /> Найти</>}
        size="large"
        style={{ marginBottom: 16 }}
      />

      {isLoading && <Spin style={{ display: 'block', textAlign: 'center', padding: 40 }} />}

      {data && !isLoading && (
        <Tabs
          items={[
            {
              key: 'all',
              label: `Все (${data.total})`,
              children: (
                <>
                  {interpretations.length === 0 && artifacts.length === 0 ? (
                    <Empty description="Ничего не найдено" />
                  ) : (
                    <>
                      {interpretations.length > 0 && (
                        <div style={{ marginBottom: 16 }}>
                          <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
                            Интерпретации ({interpretations.length})
                          </Text>
                          <List
                            dataSource={interpretations}
                            renderItem={(item: Interpretation) => (
                              <Card size="small" style={{ marginBottom: 8 }}>
                                <Space direction="vertical" size={2} style={{ width: '100%' }}>
                                  <Space>
                                    <UserOutlined />
                                    <Text strong>{item.reader_name}</Text>
                                    <LikeOutlined /> {item.likes}
                                  </Space>
                                  <Paragraph style={{ margin: 0 }} ellipsis={{ rows: 2 }}>
                                    {item.text}
                                  </Paragraph>
                                  <Space wrap>
                                    {item.themes.map((t, i) => <Tag key={i}>{t}</Tag>)}
                                  </Space>
                                </Space>
                              </Card>
                            )}
                          />
                        </div>
                      )}
                      {artifacts.length > 0 && (
                        <div>
                          <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
                            Артефакты ({artifacts.length})
                          </Text>
                          <List
                            dataSource={artifacts}
                            renderItem={(item: Artifact) => (
                              <Card size="small" style={{ marginBottom: 8 }} title={item.title}>
                                <Space direction="vertical" size={2} style={{ width: '100%' }}>
                                  <Space>
                                    <Tag color={item.category === 'archaeology' ? 'brown' : 'blue'}>
                                      {item.category}
                                    </Tag>
                                    <LikeOutlined /> {item.likes}
                                  </Space>
                                  <Paragraph style={{ margin: 0 }} ellipsis={{ rows: 2 }}>
                                    {item.description}
                                  </Paragraph>
                                </Space>
                              </Card>
                            )}
                          />
                        </div>
                      )}
                    </>
                  )}
                </>
              ),
            },
            {
              key: 'interpretations',
              label: `Интерпретации (${interpretations.length})`,
              children: interpretations.length === 0 ? (
                <Empty description="Интерпретаций не найдено" />
              ) : (
                <List
                  dataSource={interpretations}
                  renderItem={(item: Interpretation) => (
                    <Card size="small" style={{ marginBottom: 8 }}>
                      <Space direction="vertical" size={2} style={{ width: '100%' }}>
                        <Space>
                          <UserOutlined />
                          <Text strong>{item.reader_name}</Text>
                          <LikeOutlined /> {item.likes}
                        </Space>
                        <Paragraph style={{ margin: 0 }}>{item.text}</Paragraph>
                        <Space wrap>
                          {item.themes.map((t, i) => <Tag key={i}>{t}</Tag>)}
                          {item.characters.map((c, i) => <Tag key={i} color="blue">{c}</Tag>)}
                        </Space>
                      </Space>
                    </Card>
                  )}
                />
              ),
            },
            {
              key: 'artifacts',
              label: `Артефакты (${artifacts.length})`,
              children: artifacts.length === 0 ? (
                <Empty description="Артефактов не найдено" />
              ) : (
                <List
                  dataSource={artifacts}
                  renderItem={(item: Artifact) => (
                    <Card size="small" style={{ marginBottom: 8 }} title={item.title}>
                      <Space direction="vertical" size={2} style={{ width: '100%' }}>
                        <Space>
                          <Tag color={item.category === 'archaeology' ? 'brown' : 'blue'}>
                            {item.category}
                          </Tag>
                          <Text type="secondary">{item.location}</Text>
                          <LikeOutlined /> {item.likes}
                        </Space>
                        <Paragraph style={{ margin: 0 }}>{item.description}</Paragraph>
                        <Paragraph type="secondary" style={{ margin: 0, fontStyle: 'italic' }}>
                          {item.connection_to_book}
                        </Paragraph>
                      </Space>
                    </Card>
                  )}
                />
              ),
            },
          ]}
        />
      )}
    </div>
  );
}
