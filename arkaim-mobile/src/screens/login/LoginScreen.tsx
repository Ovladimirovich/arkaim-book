/**
 * Экран входа — Telegram Login Widget.
 */
import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, TextInput, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../shared/theme';
import { api } from '../../shared/api';

export function LoginScreen() {
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState('');

  const handleDevLogin = async () => {
    setLoading(true);
    try {
      const response = await api.post('/api/auth/dev-login');
      if (response.ok) {
        const data = await response.json();
        if (data.ok && data.user) {
          // Store user data and navigate to main app
          Alert.alert('Успех', `Добро пожаловать, ${data.user.display_name || 'Разработчик'}!`);
        }
      }
    } catch (error) {
      Alert.alert('Ошибка', 'Не удалось выполнить вход');
    } finally {
      setLoading(false);
    }
  };

  const handleTokenLogin = async () => {
    if (!token.trim()) {
      Alert.alert('Ошибка', 'Введите токен');
      return;
    }
    setLoading(true);
    try {
      const response = await api.post('/api/auth/login', { token });
      if (response.ok) {
        const data = await response.json();
        if (data.ok && data.user) {
          Alert.alert('Успех', `Добро пожаловать, ${data.user.display_name || 'Пользователь'}!`);
        }
      }
    } catch (error) {
      Alert.alert('Ошибка', 'Неверный токен');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>Вход в систему</Text>
        <Text style={styles.subtitle}>Получите доступ к книге «Наследие Аркаима»</Text>

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleDevLogin}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Ionicons name="code-working" size={20} color="#fff" />
              <Text style={styles.buttonText}>Войти как разработчик</Text>
            </>
          )}
        </TouchableOpacity>

        <View style={styles.divider}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>или</Text>
          <View style={styles.dividerLine} />
        </View>

        <TextInput
          style={styles.input}
          placeholder="Введите токен для входа"
          value={token}
          onChangeText={setToken}
          autoCapitalize="none"
          autoCorrect={false}
        />

        <TouchableOpacity
          style={[styles.buttonSecondary, loading && styles.buttonDisabled]}
          onPress={handleTokenLogin}
          disabled={loading}
        >
          <Ionicons name="key" size={20} color={colors.primary} />
          <Text style={styles.buttonSecondaryText}>Войти по токену</Text>
        </TouchableOpacity>

        <Text style={styles.footer}>
          Получите токен через Telegram бот или email регистрацию.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.background },
  card: { backgroundColor: colors.surface, borderRadius: 16, padding: 32, width: '90%', maxWidth: 400, alignItems: 'center' },
  title: { fontSize: 22, fontWeight: '700', color: colors.text, marginBottom: 8 },
  subtitle: { fontSize: 14, color: colors.textSecondary, marginBottom: 24, textAlign: 'center' },
  button: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: colors.primary, padding: 14, borderRadius: 8, width: '100%', marginBottom: 12, gap: 8 },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  buttonSecondary: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: 'transparent', borderWidth: 1, borderColor: colors.primary, padding: 14, borderRadius: 8, width: '100%', marginBottom: 12, gap: 8 },
  buttonSecondaryText: { color: colors.primary, fontSize: 16, fontWeight: '600' },
  divider: { flexDirection: 'row', alignItems: 'center', width: '100%', marginVertical: 16 },
  dividerLine: { flex: 1, height: 1, backgroundColor: colors.border },
  dividerText: { marginHorizontal: 12, color: colors.textMuted, fontSize: 12 },
  input: { width: '100%', borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 12, marginBottom: 12, fontSize: 14, color: colors.text },
  footer: { fontSize: 12, color: colors.textMuted, marginTop: 8, textAlign: 'center' },
});
