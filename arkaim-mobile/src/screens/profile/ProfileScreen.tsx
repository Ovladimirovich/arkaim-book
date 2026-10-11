/**
 * Экран профиля читателя.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, StyleSheet, RefreshControl } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../shared/api/client';
import { useAuth } from '../../shared/lib/auth';
import { colors, spacing } from '../../shared/theme';
import type { ReaderProfile } from '../../shared/types';

export function ProfileScreen() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<ReaderProfile | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadProfile = async () => {
    try {
      const data = await api.get<ReaderProfile>('/book/reader/profile');
      setProfile(data);
    } catch {}
  };

  useEffect(() => { loadProfile(); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadProfile();
    setRefreshing(false);
  };

  return (
    <ScrollView style={styles.container} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
      <View style={styles.header}>
        <Ionicons name="person-circle" size={64} color={colors.primary} />
        <Text style={styles.name}>{user?.display_name || user?.username || 'Читатель'}</Text>
        <Text style={styles.role}>{user?.role}</Text>
      </View>

      <View style={styles.statsRow}>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{profile?.questions_total ?? 0}</Text>
          <Text style={styles.statLabel}>Вопросов</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{profile?.conversation_count ?? 0}</Text>
          <Text style={styles.statLabel}>Диалогов</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{profile?.topics?.length ?? 0}</Text>
          <Text style={styles.statLabel}>Тем</Text>
        </View>
      </View>

      {profile?.topics && profile.topics.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Изученные темы</Text>
          {profile.topics.map((topic, i) => (
            <View key={i} style={styles.topicRow}>
              <Text style={styles.topicName}>{topic.name}</Text>
              <Text style={styles.topicDepth}>{Math.round(topic.depth * 100)}%</Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  header: { alignItems: 'center', paddingVertical: spacing.lg, backgroundColor: colors.surface },
  name: { fontSize: 20, fontWeight: '700', color: colors.text, marginTop: spacing.sm },
  role: { fontSize: 14, color: colors.textSecondary, marginTop: 4 },
  statsRow: { flexDirection: 'row', padding: spacing.md, gap: spacing.sm },
  statCard: { flex: 1, backgroundColor: colors.surface, borderRadius: 8, padding: spacing.md, alignItems: 'center' },
  statValue: { fontSize: 24, fontWeight: '700', color: colors.text },
  statLabel: { fontSize: 12, color: colors.textSecondary, marginTop: 4 },
  section: { margin: spacing.md, backgroundColor: colors.surface, borderRadius: 8, padding: spacing.md },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: colors.text, marginBottom: spacing.sm },
  topicRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: spacing.xs, borderBottomWidth: 1, borderBottomColor: colors.border },
  topicName: { fontSize: 14, color: colors.text },
  topicDepth: { fontSize: 12, color: colors.textMuted },
});
