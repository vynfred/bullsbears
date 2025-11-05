import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    files: ["**/*.{js,jsx,ts,tsx}"],
    rules: {
      // Disable overly strict rules for development
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": "off", // Disabled for development
      "@typescript-eslint/no-empty-interface": "off",
      "@typescript-eslint/ban-ts-comment": "off",

      // React specific rules
      "react/no-unescaped-entities": "off",
      "react/display-name": "off",
      "react-hooks/exhaustive-deps": "off", // Disabled for development

      // Next.js specific
      "@next/next/no-img-element": "off",

      // General JavaScript/TypeScript
      "no-console": "off", // Disabled for development
      "no-debugger": "warn",
      "prefer-const": "off", // Disabled for development
      "no-var": "error",
    },
  },
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "dist/**",
      "next-env.d.ts",
      "*.config.js",
      "*.config.mjs",
      "*.config.ts",
    ],
  },
];

export default eslintConfig;
