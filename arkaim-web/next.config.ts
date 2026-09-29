import type { NextConfig } from "next";
import bundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

const BACKEND = 'http://localhost:8642';

const nextConfig: NextConfig = {
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
        { source: '/api/:path*', destination: `${BACKEND}/:path*` },
        // Book API — /book это фронтенд-страница, а /book/* — API.
        // :path+ требует хотя бы один сегмент, чтобы /book не перехватывался.
        { source: '/book/:path+', destination: `${BACKEND}/book/:path*` },
        // Stream API — /v1/stream для SSE
        // Analytics — /analytics на верхнем уровне (без /api/ префикса)
        { source: '/analytics', destination: `${BACKEND}/analytics` },
        { source: '/v1/:path+', destination: `${BACKEND}/v1/:path*` },
      ],
    };
  },
};

export default withBundleAnalyzer(nextConfig);
