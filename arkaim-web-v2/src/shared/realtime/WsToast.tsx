/**
 * realtime/WsToast.tsx — toast-уведомления из WebSocket-событий (F5).
 *
 * Интегрируется в WsProvider: подписывается на доменные события
 * и показывает Ant Design toast.
 *
 * Toast policy (F5):
 *   new_question          → info
 *   your_question_answered → success
 *   new_suggestion        → info
 *   crowdfunding_milestone → success
 *   service_status        → warning
 *
 * pulse_beat и chat_response — НЕ toast (слишком часто / поток).
 */
'use client';

import { App } from 'antd';
import { useWsEvent } from './WsProvider';

export function WsToast() {
  // Получить instance message из Ant App context
  const { message: msgApi } = App.useApp();

  useWsEvent('new_question', () => {
    msgApi.info('Новый вопрос к книге');
  });

  useWsEvent('your_question_answered', () => {
    msgApi.success('Ответ на ваш вопрос готов');
  });

  useWsEvent('new_suggestion', () => {
    msgApi.info('Новое предложение в сообществе');
  });

  useWsEvent('crowdfunding_milestone', () => {
    msgApi.success('Новый milestone краудфандинга');
  });

  useWsEvent('service_status', () => {
    msgApi.warning('Статус сервиса обновлён');
  });

  return null;
}
