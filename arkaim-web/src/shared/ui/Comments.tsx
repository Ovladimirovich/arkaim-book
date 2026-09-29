'use client';

import { useState } from 'react';
import { List, Input, Button, Space, Typography, Empty, message } from 'antd';
import { CommentOutlined, LikeOutlined, DeleteOutlined, SendOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';

const { Text } = Typography;
const { TextArea } = Input;

type Comment = {
  id: string;
  parent_id: string;
  parent_type: string;
  reader_name: string;
  text: string;
  created_at: string;
  likes: number;
};

type CommentsProps = {
  parentType: 'interpretation' | 'artifact';
  parentId: string;
};

export function Comments({ parentType, parentId }: CommentsProps) {
  const [text, setText] = useState('');
  const queryClient = useQueryClient();
  const queryKey = ['comments', parentType, parentId];

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: () => api.get<{ comments: Comment[] }>(`/book/community/comments/${parentType}/${parentId}`),
  });

  const addMutation = useMutation({
    mutationFn: (values: { text: string }) =>
      api.post(`/book/community/comments/${parentType}/${parentId}`, values),
    onSuccess: () => {
      message.success('Комментарий добавлен');
      queryClient.invalidateQueries({ queryKey });
      setText('');
    },
  });

  const likeMutation = useMutation({
    mutationFn: (id: string) => api.post(`/book/community/comments/${id}/like`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  const comments = data?.comments || [];

  return (
    <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #f0f0f0' }}>
      <Space style={{ marginBottom: 8 }}>
        <CommentOutlined />
        <Text type="secondary">Комментарии ({comments.length})</Text>
      </Space>

      {comments.length === 0 ? (
        <Empty description="Пока нет комментариев" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <List
          size="small"
          dataSource={comments}
          renderItem={(item: Comment) => (
            <List.Item style={{ padding: '8px 0' }}>
              <Space direction="vertical" size={2} style={{ width: '100%' }}>
                <Space>
                  <Text strong style={{ fontSize: 13 }}>{item.reader_name || 'Читатель'}</Text>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {new Date(item.created_at).toLocaleString('ru')}
                  </Text>
                </Space>
                <Text style={{ fontSize: 13 }}>{item.text}</Text>
                <Button
                  size="small"
                  type="text"
                  icon={<LikeOutlined />}
                  onClick={() => likeMutation.mutate(item.id)}
                >
                  {item.likes}
                </Button>
              </Space>
            </List.Item>
          )}
        />
      )}

      <div style={{ marginTop: 8 }}>
        <TextArea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Напишите комментарий..."
          autoSize={{ minRows: 1, maxRows: 3 }}
          style={{ marginBottom: 8 }}
        />
        <Button
          type="primary"
          size="small"
          icon={<SendOutlined />}
          onClick={() => addMutation.mutate({ text })}
          loading={addMutation.isPending}
          disabled={!text.trim()}
        >
          Отправить
        </Button>
      </div>
    </div>
  );
}
