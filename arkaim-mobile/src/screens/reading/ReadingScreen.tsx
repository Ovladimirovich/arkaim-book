/**
 * Экран чтения — главы книги.
 */
import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../shared/theme';
import { api } from '../../shared/api';

type Chapter = {
  id: string;
  title: string;
  chapter_number: number;
  description?: string;
};

export function ReadingScreen() {
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);

  useEffect(() => {
    loadChapters();
  }, []);

  const loadChapters = async () => {
    try {
      const data = await api.get('/book/chapters');
      setChapters(data?.chapters || []);
    } catch (error) {
      console.error('Failed to load chapters:', error);
    } finally {
      setLoading(false);
    }
  };

  if (selectedChapter) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => setSelectedChapter(null)}>
            <Ionicons name="arrow-back" size={24} color={colors.primary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>{selectedChapter.title}</Text>
        </View>
        <View style={styles.content}>
          <Text style={styles.chapterNumber}>Глава {selectedChapter.chapter_number}</Text>
          <Text style={styles.description}>{selectedChapter.description || 'Нет описания'}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Чтение</Text>
      {loading ? (
        <ActivityIndicator size="large" color={colors.primary} style={styles.loader} />
      ) : (
        <FlatList
          data={chapters}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.chapterItem}
              onPress={() => setSelectedChapter(item)}
            >
              <View style={styles.chapterIcon}>
                <Text style={styles.chapterNumber}>{item.chapter_number}</Text>
              </View>
              <View style={styles.chapterInfo}>
                <Text style={styles.chapterTitle}>{item.title}</Text>
                {item.description && (
                  <Text style={styles.chapterDescription} numberOfLines={2}>
                    {item.description}
                  </Text>
                )}
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
            </TouchableOpacity>
          )}
          ListEmptyComponent={
            <Text style={styles.emptyText}>Нет доступных глав</Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  title: { fontSize: 24, fontWeight: '700', color: colors.text, padding: 16 },
  header: { flexDirection: 'row', alignItems: 'center', padding: 16, gap: 12 },
  headerTitle: { fontSize: 18, fontWeight: '600', color: colors.text, flex: 1 },
  loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  chapterItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  chapterIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.primary + '20',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  chapterNumber: { fontSize: 16, fontWeight: '700', color: colors.primary },
  chapterInfo: { flex: 1 },
  chapterTitle: { fontSize: 16, fontWeight: '600', color: colors.text, marginBottom: 4 },
  chapterDescription: { fontSize: 14, color: colors.textSecondary },
  content: { padding: 16 },
  description: { fontSize: 16, color: colors.textSecondary, lineHeight: 24 },
  emptyText: { textAlign: 'center', color: colors.textMuted, marginTop: 40 },
});
