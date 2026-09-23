/**
 * useStreamingChat — streaming-чат через streamAsk из shared/api.
 *
 * session_id генерируется один раз при монтировании хука.
 * accumulated хранится в useRef чтобы onDone мог прочитать финальный текст.
 */
'use client';

import { useCallback, useRef, useState } from 'react';
import type { AskAnswer } from '@/shared/api/contracts/book';
import { streamAsk } from '@/shared/api/contracts/book';

export interface StreamingChatState {
  text: string;
  streaming: boolean;
  error: string | null;
  messages: Array<{ role: 'user' | 'assistant'; content: string; metadata?: AskAnswer }>;
}

interface InternalMsg {
  role: 'user' | 'assistant';
  content: string;
  metadata?: AskAnswer;
}

export function useStreamingChat() {
  const [state, setState] = useState<StreamingChatState>({
    text: '',
    streaming: false,
    error: null,
    messages: [],
  });

  const sessionIdRef = useRef<string | undefined>(undefined);
  if (!sessionIdRef.current) {
    sessionIdRef.current =
      typeof crypto !== 'undefined'
        ? crypto.randomUUID()
        : `session-${Date.now()}`;
  }

  // Ref for accumulated text — onDone closes over this ref, not a stale variable.
  const accumulatedRef = useRef('');
  const lastQuestionRef = useRef('');

  const sendMessage = useCallback(async (question: string, existingMessages?: InternalMsg[]) => {
    setState((prev) => ({ ...prev, streaming: true, error: null }));
    accumulatedRef.current = '';
    lastQuestionRef.current = question;

    const history = (existingMessages ?? []).map((m) => ({
      role: m.role,
      content: m.content,
    }));
    history.push({ role: 'user', content: question });

    try {
      await streamAsk({
        messages: history,
        session_id: sessionIdRef.current,
        onToken: (token) => {
          accumulatedRef.current += token;
          setState((prev) => ({ ...prev, text: accumulatedRef.current, error: null }));
        },
        onDone: () => {
          setState((prev) => {
            const updatedMessages = [
              ...prev.messages,
              { role: 'user' as const, content: lastQuestionRef.current },
              { role: 'assistant' as const, content: accumulatedRef.current },
            ];
            return {
              text: '',
              streaming: false,
              error: null,
              messages: updatedMessages,
            };
          });
        },
        onError: (err) => {
          setState((prev) => ({ ...prev, streaming: false, error: String(err) }));
        },
      });
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        setState((prev) => ({
          ...prev,
          streaming: false,
          error: e instanceof Error ? e.message : String(e),
        }));
      }
    }
  }, []);

  const reset = useCallback(() => {
    setState({ text: '', streaming: false, error: null, messages: [] });
    sessionIdRef.current =
      typeof crypto !== 'undefined'
        ? crypto.randomUUID()
        : `session-${Date.now()}`;
  }, []);

  return { ...state, sendMessage, reset };
}