import { defineConfig } from 'tsup'

/**
 * Two artifacts, one build:
 *
 * - `dist/index.js` and `dist/lib/*.js` are the Host bundle. `bundle: false`
 *   keeps one readable module per source file, so stack traces and the plugin's
 *   own unit tests point at the file that failed rather than a generated chunk.
 * - `dist/client.js` is the browser artifact. It is a single self-contained
 *   script: the DSH module loader supplies `require('react')`, so nothing is
 *   imported at build time and no React copy is bundled.
 */
export default defineConfig({
  entry: ['src/index.js', 'src/client.js', 'src/lib/*.js', 'src/lib/*.ts'],
  format: ['esm'],
  target: ['node22', 'es2020'],
  platform: 'neutral',
  bundle: false,
  splitting: false,
  clean: true,
  dts: false,
  sourcemap: true,
  treeshake: false,
  outDir: 'dist',
})
