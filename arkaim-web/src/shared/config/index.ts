/**
 * Конфигурация приложения.
 */

export const config = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8642',
  },
  ws: {
    url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8642',
  },
  features: {
    visualGenome: true,
    crowdfunding: true,
    xray: true,
    emailDigest: true,
  },
} as const;
