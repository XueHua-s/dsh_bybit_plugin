import { defineConfig } from 'tsdown'

/**
 * Keep Host modules importable by Node while making Client a single DSH loader script.
 * The DSH client loader injects React at runtime; the client bundle keeps that require call.
 */
export default defineConfig([
  {
    entry: ['src/index.ts', 'src/lib/**/*.ts'],
    format: 'esm',
    target: 'node22',
    platform: 'node',
    unbundle: true,
    sourcemap: true,
    clean: true,
    outDir: 'dist',
    outExtensions: () => ({ js: '.js' }),
    dts: true,
  },
  {
    entry: ['src/client.ts'],
    format: 'esm',
    target: 'es2020',
    platform: 'browser',
    sourcemap: true,
    clean: false,
    outDir: 'dist',
    outExtensions: () => ({ js: '.js' }),
    dts: false,
  },
])
