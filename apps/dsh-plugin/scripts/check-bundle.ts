#!/usr/bin/env node
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { tmpdir } from 'node:os'
import { spawnSync } from 'node:child_process'
import { pnpmEnvironment } from './pnpm-environment.ts'

const root = resolve(decodeURIComponent(new URL('..', import.meta.url).pathname))
const manifest = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'))
for (const version of Object.values(manifest.dependencies ?? {})) {
  if (typeof version === 'string' && version.startsWith('workspace:')) throw new Error('runtime bundle dependencies must not use workspace protocol')
}
const required: Array<[string[], string]> = [
  [['main'], './dist/index.js'],
  [['exports', '.'], './dist/index.js'],
  [['exports', './client'], './dist/client.js'],
  [['dsh', 'bundle', 'patch'], './cordis.patch.yml'],
  [['dsh', 'client', 'platform'], 'web'],
]
for (const [path, expected] of required) {
  const value = path.reduce((current, key) => current?.[key], manifest)
  if (value !== expected) throw new Error(`${path.join('.')} must be ${expected}`)
}
for (const file of ['cordis.patch.yml', 'dist/index.js', 'dist/client.js', 'docs/DETAIL.md', 'locale/en.json', 'locale/zh.json']) {
  if (!existsSync(resolve(root, file))) throw new Error(`missing bundle artifact: ${file}`)
}
for (const locale of ['en', 'zh']) {
  const dictionary = JSON.parse(readFileSync(resolve(root, `locale/${locale}.json`), 'utf8')) as { meta?: { detail?: unknown } }
  const detail = dictionary.meta?.detail
  if (typeof detail !== 'string' || detail !== 'docs/DETAIL.md') {
    throw new Error(`locale/${locale}.json meta.detail must be docs/DETAIL.md`)
  }
  if (!existsSync(resolve(root, detail))) throw new Error(`locale/${locale}.json detail target is missing: ${detail}`)
}
const patch = readFileSync(resolve(root, 'cordis.patch.yml'), 'utf8')
if (!patch.includes(`name: '${manifest.name}'`)) throw new Error('cordis.patch.yml does not insert the Host plugin row')
if (patch.includes('apiKey:') || patch.includes('apiSecret:')) throw new Error('bundle patch must not contain credentials')
console.log('bundle metadata, Host/Client entries, patch and credential boundary: ok')

// Exercise pnpm's published manifest and import the extracted archive without workspace modules.
const isolated = mkdtempSync(join(tmpdir(), 'bybit-bundle-'))
try {
  const pack = spawnSync('pnpm', ['pack', '--pack-destination', isolated], { cwd: root, encoding: 'utf8', env: pnpmEnvironment() })
  if (pack.status !== 0) throw new Error(`bundle pack failed: ${pack.stderr}`)
  const archive = readdirSync(isolated).find(file => file.endsWith('.tgz'))
  if (!archive) throw new Error('bundle pack archive is missing')
  const extract = spawnSync('tar', ['-xzf', join(isolated, archive), '-C', isolated], { encoding: 'utf8' })
  if (extract.status !== 0) throw new Error(`bundle extraction failed: ${extract.stderr}`)
  const packedRoot = join(isolated, 'package')
  const packed = JSON.parse(readFileSync(join(packedRoot, 'package.json'), 'utf8')) as { dependencies?: Record<string, string> }
  if (Object.keys(packed.dependencies ?? {}).length !== 0) throw new Error('Host dist must not require external runtime dependencies')
  const result = spawnSync(process.execPath, ['--input-type=module', '-e', "const plugin = await import('./dist/index.js'); if (typeof plugin.apply !== 'function') process.exit(1)"], { cwd: packedRoot, encoding: 'utf8', env: { ...process.env, NODE_PATH: '' } })
  if (result.status !== 0) throw new Error(`isolated bundle import failed: ${result.stderr}`)
  console.log('packed manifest has no runtime deps; isolated extracted Host import without node_modules: ok')
} finally {
  rmSync(isolated, { recursive: true, force: true })
}
