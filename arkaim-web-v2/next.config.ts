import type { NextConfig } from "next";

// Backend — единственный source of truth (FRONTEND_ARCHITECTURE).
// Проксирование повторяет утверждённые rewrites legacy (проверены forensic-аудитом):
// /auth, /xray — beforeFiles (нет фронтенд-страниц верхнего уровня),
// /book, /v1, /analytics, /api — afterFiles.
const BACKEND = process.env.BACKEND_URL || 'http://localhost:8642';

const nextConfig: NextConfig = {
  // TS-проверка — отдельный гейт (`tsc --noEmit` в CI + lint), а build
  // в sandbox-среде падает на спавне TS-worker (EPERM). CI запускает
  // typecheck самостоятельно ПЕРЕД build.
  typescript: { ignoreBuildErrors: true },
  // Sandbox-среда разработки блокирует pipe-спавн дочерних процессов сборки.
  // workerThreads: jest-worker использует worker_threads (не child_process) —
  // сборка работает в ограниченной среде. На CI не влияет (эквивалентно).
  experimental: { cpus: 1, workerThreads: true },
  async rewrites() {
    return {
      beforeFiles: [
        { source: '/auth/:path+', destination: `${BACKEND}/auth/:path*` },
        { source: '/xray/:path+', destination: `${BACKEND}/xray/:path*` },
      ],
      afterFiles: [
        { source: '/api/:path*', destination: `${BACKEND}/:path*` },
        { source: '/book/:path+', destination: `${BACKEND}/book/:path*` },
        { source: '/analytics', destination: `${BACKEND}/analytics` },
        { source: '/v1/:path+', destination: `${BACKEND}/v1/:path*` },
      ],
    };
  },
};

export default nextConfig;
