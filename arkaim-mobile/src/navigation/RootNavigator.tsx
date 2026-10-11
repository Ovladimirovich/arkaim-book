/**
 * Корневой навигатор приложения.
 */
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';

import { LoginScreen } from '../screens/login/LoginScreen';
import { ChatScreen } from '../screens/chat/ChatScreen';
import { ProfileScreen } from '../screens/profile/ProfileScreen';
import { HistoryScreen } from '../screens/history/HistoryScreen';
import { AdminScreen } from '../screens/admin/AdminScreen';
import { ReadingScreen } from '../screens/reading/ReadingScreen';
import { SearchScreen } from '../screens/search/SearchScreen';
import { NotificationsScreen } from '../screens/notifications/NotificationsScreen';
import { AuthProvider, useAuth } from '../shared/lib/auth';
import { colors } from '../shared/theme';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function MainTabs() {
  const { user } = useAuth();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: keyof typeof Ionicons.glyphMap = 'chatbubble';
          if (route.name === 'Chat') iconName = focused ? 'chatbubble' : 'chatbubble-outline';
          else if (route.name === 'Reading') iconName = focused ? 'book' : 'book-outline';
          else if (route.name === 'Search') iconName = focused ? 'search' : 'search-outline';
          else if (route.name === 'Notifications') iconName = focused ? 'notifications' : 'notifications-outline';
          else if (route.name === 'Profile') iconName = focused ? 'person' : 'person-outline';
          else if (route.name === 'History') iconName = focused ? 'time' : 'time-outline';
          else if (route.name === 'Admin') iconName = focused ? 'settings' : 'settings-outline';
          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        headerStyle: { backgroundColor: colors.navBg },
        headerTintColor: colors.navText,
      })}
    >
      <Tab.Screen name="Chat" component={ChatScreen} options={{ title: 'Чат с книгой' }} />
      <Tab.Screen name="Reading" component={ReadingScreen} options={{ title: 'Чтение' }} />
      <Tab.Screen name="Search" component={SearchScreen} options={{ title: 'Поиск' }} />
      <Tab.Screen name="Notifications" component={NotificationsScreen} options={{ title: 'Уведомления' }} />
      <Tab.Screen name="Profile" component={ProfileScreen} options={{ title: 'Профиль' }} />
      <Tab.Screen name="History" component={HistoryScreen} options={{ title: 'История' }} />
      {user?.role === 'admin' && (
        <Tab.Screen name="Admin" component={AdminScreen} options={{ title: 'Админ' }} />
      )}
    </Tab.Navigator>
  );
}

function AppNavigator() {
  const { user, loading } = useAuth();

  if (loading) return null;

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {!user ? (
          <Stack.Screen name="Login" component={LoginScreen} />
        ) : (
          <Stack.Screen name="Main" component={MainTabs} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export function RootNavigator() {
  return (
    <AuthProvider>
      <AppNavigator />
    </AuthProvider>
  );
}
