/**
 * Экран истории вопросов.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../shared/api/client';
import { colors, spacing } from '../../shared/theme';

type HistoryItem = { id: number; session_id: string; content: string; created_at: string };

export function HistoryScreen() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const loadHistory = async () => {
    try {
      const data = await api.get<{ data: HistoryItem[] }>('/book/reader/history?limit=50');
      setHistory(data.data || []);
    } catch {}
  };

  useEffect(() => { loadHistory(); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadHistory();
    setRefreshing(false);
  };

  const renderItem = ({ item }: { item: HistoryItem }) => (
    <TouchableOpacity style={styles.item}>
      <View style={styles.itemContent}>
        <Text style={styles.question} numberOfLines={2}>{item.content}</Text>
        <Text style={styles.date}>{new Date(item.created_at).toLocaleString('ru')}</Text>
      </View>
      <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={history}
        renderItem={renderItem}
        keyExtractor={item => String(item.id)}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="time-outline" size={48} color={colors.textMuted} />
            <Text style={styles.emptyText}>Нет истории вопросов</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  list: { padding: spacing.md },
  item: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.surface, borderRadius: 8, padding: spacing.md, marginBottom: spacing.sm },
  itemContent: { flex: 1 },
  question: { fontSize: 14, color: colors.text, marginBottom: 4 },
  date: { fontSize: 12, color: colors.textMuted },
  empty: { alignItems: 'center', paddingVertical: 64 },
  emptyText: { fontSize: 14, color: colors.textMuted, marginTop: spacing.sm },
});
