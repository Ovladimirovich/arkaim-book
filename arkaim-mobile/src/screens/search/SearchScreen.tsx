/**
 * Экран поиска — поиск по знаниям.
 */
import React, { useState } from 'react';
import { View, Text, TextInput, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../shared/theme';
import { api } from '../../shared/api';

type SearchResult = {
  id: string;
  title: string;
  type: string;
  description?: string;
};

export function SearchScreen() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await api.get(`/book/search?q=${encodeURIComponent(query)}&limit=20`);
      setResults(data?.results || []);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Поиск</Text>
      <View style={styles.searchBar}>
        <Ionicons name="search" size={20} color={colors.textMuted} />
        <TextInput
          style={styles.input}
          placeholder="Поиск знаний, тем, персонажей..."
          value={query}
          onChangeText={setQuery}
          onSubmitEditing={search}
          returnKeyType="search"
        />
        {query.length > 0 && (
          <TouchableOpacity onPress={() => { setQuery(''); setResults([]); }}>
            <Ionicons name="close-circle" size={20} color={colors.textMuted} />
          </TouchableOpacity>
        )}
      </View>

      {loading ? (
        <ActivityIndicator size="large" color={colors.primary} style={styles.loader} />
      ) : (
        <FlatList
          data={results}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TouchableOpacity style={styles.resultItem}>
              <View style={[styles.typeBadge, { backgroundColor: getTypeColor(item.type) }]}>
                <Text style={styles.typeText}>{item.type}</Text>
              </View>
              <View style={styles.resultInfo}>
                <Text style={styles.resultTitle}>{item.title}</Text>
                {item.description && (
                  <Text style={styles.resultDescription} numberOfLines={2}>
                    {item.description}
                  </Text>
                )}
              </View>
            </TouchableOpacity>
          )}
          ListEmptyComponent={
            query.length > 0 && !loading ? (
              <Text style={styles.emptyText}>Ничего не найдено</Text>
            ) : (
              <Text style={styles.emptyText}>Введите запрос для поиска</Text>
            )
          }
        />
      )}
    </View>
  );
}

function getTypeColor(type: string): string {
  switch (type) {
    case 'theme': return '#722ed1';
    case 'character': return '#1890ff';
    case 'value': return '#52c41a';
    case 'location': return '#fa8c16';
    default: return '#8c8c8c';
  }
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  title: { fontSize: 24, fontWeight: '700', color: colors.text, padding: 16 },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    margin: 16,
    padding: 12,
    borderRadius: 12,
    gap: 8,
  },
  input: { flex: 1, fontSize: 16, color: colors.text },
  loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  resultItem: {
    flexDirection: 'row',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  typeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    marginRight: 12,
    alignSelf: 'flex-start',
  },
  typeText: { fontSize: 12, color: '#fff', fontWeight: '600' },
  resultInfo: { flex: 1 },
  resultTitle: { fontSize: 16, fontWeight: '600', color: colors.text, marginBottom: 4 },
  resultDescription: { fontSize: 14, color: colors.textSecondary },
  emptyText: { textAlign: 'center', color: colors.textMuted, marginTop: 40 },
});
