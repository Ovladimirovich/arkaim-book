import type { NextConfig } from "next";
import bundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8642';

const nextConfig: NextConfig = {
  // Security headers для всех ответов
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        ],
      },
    ];
  },
  async rewrites() {
    return {
      // beforeFiles — выполняются ДО проверки файловой системы.
      // Auth — /auth/* нет фронтенд-страниц, всегда проксируем на бэкенд.
      beforeFiles: [
        { source: '/auth/:path+', destination: `${BACKEND}/auth/:path*` },
        // XRay API — нет фронтенд-страниц /xray/*
        { source: '/xray/:path+', destination: `${BACKEND}/xray/:path*` },
      ],
      // afterFiles — выполняются ПОСЛЕ проверки файловой системы.
      // Локальные API routes (src/app/api/*) обрабатываются Next.js первыми.
      // Остальные /api/* проксируются на бэкенд.
      afterFiles: [
        // Q3: очередь проверки кандидатов. Бэкенд слушает /api/candidates
        // (суффикс /api — часть пути, в отличие от большинства роутов).
        // Обязательно ДО общего /api/:path*, иначе /api/ срежется и
        // бэкенд получит /candidates → 404.
        { source: '/api/candidates/:path*', destination: `${BACKEND}/api/candidates/:path*` },
        { source: '/api/:path*', destination: `${BACKEND}/:path*` },
        // Book API — /book это фронтенд-страница, а /book/* — API.
        // :path+ требует хотя бы один сегмент, чтобы /book не перехватывался.
        { source: '/book/:path+', destination: `${BACKEND}/book/:path*` },
        { source: '/knowledge/cards/:path+', destination: `${BACKEND}/knowledge/cards/:path*` },
        // Stream API — /v1/stream для SSE
        // Analytics — /analytics на верхнем уровне (без /api/ префикса)
        { source: '/analytics', destination: `${BACKEND}/analytics` },
        { source: '/v1/:path+', destination: `${BACKEND}/v1/:path*` },
      ],
    };
  },
};

export default withBundleAnalyzer(nextConfig);
