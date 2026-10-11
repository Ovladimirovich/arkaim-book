/**
 * Экран админ-панели (упрощённый для мобильного).
 */
import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../shared/api/client';
import { colors, spacing } from '../../shared/theme';

type User = { id: string; role: string; username?: string; display_name?: string; is_active: boolean };

export function AdminScreen() {
  const [users, setUsers] = useState<User[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const loadUsers = async () => {
    try {
      const data = await api.get<User[]>('/auth/admin/users');
      setUsers(data || []);
    } catch {}
  };

  useEffect(() => { loadUsers(); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadUsers();
    setRefreshing(false);
  };

  const renderItem = ({ item }: { item: User }) => (
    <View style={styles.userRow}>
      <View style={styles.userInfo}>
        <Text style={styles.userName}>{item.display_name || item.username || item.id.slice(0, 8)}</Text>
        <Text style={styles.userRole}>{item.role}</Text>
      </View>
      <View style={[styles.statusDot, { backgroundColor: item.is_active ? colors.success : colors.danger }]} />
    </View>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Пользователи</Text>
        <Text style={styles.count}>{users.length} чел.</Text>
      </View>
      <FlatList
        data={users}
        renderItem={renderItem}
        keyExtractor={item => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        contentContainerStyle={styles.list}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: spacing.md },
  title: { fontSize: 18, fontWeight: '600', color: colors.text },
  count: { fontSize: 14, color: colors.textSecondary },
  list: { padding: spacing.md },
  userRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.surface, borderRadius: 8, padding: spacing.md, marginBottom: spacing.sm },
  userInfo: { flex: 1 },
  userName: { fontSize: 14, fontWeight: '500', color: colors.text },
  userRole: { fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  statusDot: { width: 10, height: 10, borderRadius: 5 },
});
