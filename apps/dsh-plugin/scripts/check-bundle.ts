#!/usr/bin/env node
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(decodeURIComponent(new URL('..', import.meta.url).pathname))
const manifest = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'))
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
