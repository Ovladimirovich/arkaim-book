/**
 * Экран чата с книгой.
 */
import React, { useState, useRef, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../shared/api/client';
import { colors, spacing } from '../../shared/theme';
import type { ChatMessage } from '../../shared/types';

export function ChatScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    flatListRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || sending) return;
    const question = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: question }]);
    setSending(true);

    try {
      const result = await api.post<{ data: { answer: string; source?: string } }>('/book/ask', { question });
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: result.data.answer,
        source: result.data.source,
      }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Извините, произошла ошибка.' }]);
    } finally {
      setSending(false);
    }
  };

  const renderMessage = ({ item }: { item: ChatMessage }) => (
    <View style={[styles.message, item.role === 'user' ? styles.userMessage : styles.bookMessage]}>
      <View style={[styles.avatar, item.role === 'user' ? styles.userAvatar : styles.bookAvatar]}>
        <Ionicons name={item.role === 'user' ? 'person' : 'chatbubble'} size={16} color="#fff" />
      </View>
      <View style={[styles.bubble, item.role === 'user' ? styles.userBubble : styles.bookBubble]}>
        <Text style={styles.messageText}>{item.content}</Text>
        {item.source && <Text style={styles.source}>{item.source}</Text>}
      </View>
    </View>
  );

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(_, i) => String(i)}
        contentContainerStyle={styles.messageList}
      />
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="Ваш вопрос..."
          multiline
          maxLength={2000}
          editable={!sending}
        />
        <TouchableOpacity style={styles.sendButton} onPress={sendMessage} disabled={sending}>
          <Ionicons name="send" size={20} color="#fff" />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  messageList: { padding: spacing.md },
  message: { flexDirection: 'row', marginBottom: spacing.sm, maxWidth: '85%' },
  userMessage: { alignSelf: 'flex-end', flexDirection: 'row-reverse' },
  bookMessage: { alignSelf: 'flex-start' },
  avatar: { width: 32, height: 32, borderRadius: 16, justifyContent: 'center', alignItems: 'center', marginHorizontal: spacing.xs },
  userAvatar: { backgroundColor: '#dbeafe' },
  bookAvatar: { backgroundColor: colors.navBg },
  bubble: { padding: spacing.sm, borderRadius: 12, maxWidth: '80%' },
  userBubble: { backgroundColor: colors.primary, borderBottomRightRadius: 4 },
  bookBubble: { backgroundColor: colors.surface, borderBottomLeftRadius: 4 },
  messageText: { fontSize: 14, lineHeight: 20 },
  source: { fontSize: 11, color: colors.textMuted, marginTop: 4 },
  inputRow: { flexDirection: 'row', padding: spacing.sm, backgroundColor: colors.surface, borderTopWidth: 1, borderTopColor: colors.border },
  input: { flex: 1, borderWidth: 1, borderColor: colors.border, borderRadius: 8, paddingHorizontal: spacing.sm, paddingVertical: spacing.xs, fontSize: 14, maxHeight: 100 },
  sendButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.primary, justifyContent: 'center', alignItems: 'center', marginLeft: spacing.sm },
});
