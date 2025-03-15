import js from '@eslint/js';
import ts from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';

export default [
  js.configs.recommended,
  {
    files: ['src/**/*.ts', 'src/**/*.tsx'],
    ignores: [
      'node_modules/',
      'dist/',
      'build/'
    ],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 'latest',
      sourceType: 'module'
    },
    plugins: {
      '@typescript-eslint': ts
    },
    rules: {
      // Add your rules here
    }
  }
];