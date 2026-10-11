/**
 * Экран уведомлений — Live-лента и WebSocket.
 */
import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../shared/theme';
import { api } from '../../shared/api';

type Notification = {
  id: string;
  type: string;
  title: string;
  message: string;
  created_at: string;
  read: boolean;
};

export function NotificationsScreen() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadNotifications();
  }, []);

  const loadNotifications = async () => {
    try {
      const data = await api.get('/notifications?limit=50');
      setNotifications(data?.notifications || []);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (id: string) => {
    try {
      await api.post(`/notifications/${id}/read`);
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, read: true } : n)
      );
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'suggestion': return 'bulb';
      case 'trending': return 'trending-up';
      case 'system': return 'information-circle';
      default: return 'notifications';
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Уведомления</Text>
      {loading ? (
        <ActivityIndicator size="large" color={colors.primary} style={styles.loader} />
      ) : (
        <FlatList
          data={notifications}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[styles.notificationItem, !item.read && styles.unread]}
              onPress={() => markAsRead(item.id)}
            >
              <View style={styles.iconContainer}>
                <Ionicons
                  name={getNotificationIcon(item.type)}
                  size={24}
                  color={item.read ? colors.textMuted : colors.primary}
                />
              </View>
              <View style={styles.notificationInfo}>
                <Text style={[styles.notificationTitle, !item.read && styles.unreadTitle]}>
                  {item.title}
                </Text>
                <Text style={styles.notificationMessage} numberOfLines={2}>
                  {item.message}
                </Text>
                <Text style={styles.notificationTime}>
                  {new Date(item.created_at).toLocaleString()}
                </Text>
              </View>
              {!item.read && <View style={styles.unreadBadge} />}
            </TouchableOpacity>
          )}
          ListEmptyComponent={
            <Text style={styles.emptyText}>Нет уведомлений</Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  title: { fontSize: 24, fontWeight: '700', color: colors.text, padding: 16 },
  loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  notificationItem: {
    flexDirection: 'row',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  unread: { backgroundColor: colors.primary + '08' },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.surface,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  notificationInfo: { flex: 1 },
  notificationTitle: { fontSize: 16, fontWeight: '600', color: colors.text, marginBottom: 4 },
  unreadTitle: { color: colors.primary },
  notificationMessage: { fontSize: 14, color: colors.textSecondary, marginBottom: 4 },
  notificationTime: { fontSize: 12, color: colors.textMuted },
  unreadBadge: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.primary,
    alignSelf: 'flex-start',
    marginTop: 4,
  },
  emptyText: { textAlign: 'center', color: colors.textMuted, marginTop: 40 },
});
