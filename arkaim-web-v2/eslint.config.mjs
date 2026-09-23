import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Generated artifacts — не правятся руками и не линтятся
    "src/shared/api/generated/**",
    "src/shared/rbac/generated/**",
    "contracts/openapi.json",
  ]),
  // ── Красные линии F1 (FRONTEND_ARCHITECTURE §2, F1_SPEC §3) ──
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      // R-ARC: сетевые вызовы только через typed contract-слой
      "no-restricted-syntax": [
        "error",
        {
          selector: "CallExpression[callee.name='fetch']",
          message: "Прямой fetch запрещён вне shared/api — используйте typed contracts (@/shared/api).",
        },
      ],
      "no-restricted-globals": [
        "error",
        {
          name: "WebSocket",
          message: "Прямой WebSocket запрещён вне shared/realtime — используйте ws-client.",
        },
      ],
    },
  },
  {
    // shared/api и shared/realtime — единственные места с сетевым доступом
    files: ["src/shared/api/**", "src/shared/realtime/**", "src/app/api/**"],
    rules: {
      "no-restricted-syntax": "off",
      "no-restricted-globals": "off",
    },
  },
]);

export default eslintConfig;
