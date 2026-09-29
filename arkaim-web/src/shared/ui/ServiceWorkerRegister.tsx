'use client';

import { useEffect } from 'react';

export function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!('serviceWorker' in navigator)) return;

    // В dev-режиме старый Service Worker может продолжать отдавать устаревшие
    // Next/Turbopack chunks. Активно снимаем его и удаляем PWA-кэши Arkaim.
    if (process.env.NODE_ENV === 'development') {
      navigator.serviceWorker.getRegistrations()
        .then((registrations) => {
          registrations.forEach((registration) => {
            void registration.unregister();
          });
        })
        .catch(() => {});

      if ('caches' in window) {
        caches.keys()
          .then((cacheNames) => Promise.all(
            cacheNames
              .filter((name) => name.startsWith('arkaim-'))
              .map((name) => caches.delete(name))
          ))
          .catch(() => {});
      }

      return;
    }

    navigator.serviceWorker.register('/sw.js').catch(() => {
      // SW registration failed — silently ignore
    });
  }, []);

  return null;
}
