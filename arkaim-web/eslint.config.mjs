import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Legacy pages intentionally use dynamic data shapes while contracts are migrated.
  // Keep these checks from blocking the functional transformation; new code should
  // still be typed explicitly and can opt back into these rules incrementally.
  // TODO(typed-contracts): после миграции всех страниц на @/shared/api/contracts
  // вернуть "@typescript-eslint/no-explicit-any": "error" и удалить этот override.
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/static-components": "off",
      "react-hooks/immutability": "off"
    }
  },
  // Новый код (typed contracts) — строже: any запрещён
  {
    files: ["src/shared/api/**/*.ts", "src/shared/api/**/*.tsx"],
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts"
  ])
]);

export default eslintConfig;