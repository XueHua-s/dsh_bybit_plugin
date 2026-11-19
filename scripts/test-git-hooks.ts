import assert from 'node:assert/strict'
import { execFileSync, spawnSync } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const hook = resolve(dirname(fileURLToPath(import.meta.url)), 'git-hooks.ts')
const realGit = execFileSync('which', ['git'], { encoding: 'utf8' }).trim()
const realScanner = execFileSync('which', ['gitleaks'], { encoding: 'utf8' }).trim()
const root = mkdtempSync(join(tmpdir(), 'bybit-hook-fixture-'))
let passed = 0

function fixture(name: string): { cwd: string; bin: string; log: string } {
  const cwd = join(root, name)
  const bin = join(cwd, 'bin')
  const log = join(cwd, 'commands.jsonl')
  mkdirSync(bin, { recursive: true })
  execFileSync(realGit, ['init', '-q', cwd])
  writeFileSync(log, '')
  for (const command of ['git', 'pnpm', 'uv', 'gitleaks']) {
    const script = `#!${process.execPath}
const fs = require('node:fs');
const cp = require('node:child_process');
fs.appendFileSync(${JSON.stringify(log)}, JSON.stringify([${JSON.stringify(command)}, ...process.argv.slice(2)]) + '\\n');
${command === 'git'
  ? `const result = cp.spawnSync(${JSON.stringify(realGit)}, process.argv.slice(2), {stdio:'inherit'}); process.exit(result.status ?? 1);`
  : 'process.exit(0);'}
`
    executable(join(bin, command), script)
  }
  return { cwd, bin, log }
}

function executable(path: string, source: string): void {
  writeFileSync(path, source)
  chmodSync(path, 0o755)
}

function stage(cwd: string, path: string, content = 'export const fixture = true\n'): void {
  mkdirSync(dirname(join(cwd, path)), { recursive: true })
  writeFileSync(join(cwd, path), content)
  execFileSync(realGit, ['add', '--', path], { cwd })
}

function run(cwd: string, bin: string, mode = 'pre-commit') {
  return spawnSync(process.execPath, [hook, mode], {
    cwd, encoding: 'utf8', env: { ...process.env, PATH: bin },
  })
}

function commands(log: string): string[][] {
  return readFileSync(log, 'utf8').trim().split('\n').filter(Boolean).map(line => JSON.parse(line) as string[])
}

try {
  const denied = fixture('nested-sensitive')
  stage(denied.cwd, 'apps/example/.env.production', 'fixture contents must remain unread\n')
  const deniedResult = run(denied.cwd, denied.bin)
  assert.equal(deniedResult.status, 1)
  assert.match(deniedResult.stderr, /Contents were not read/)
  assert.equal(commands(denied.log).length, 1, 'Only filename query may run before sensitive rejection')
  passed++

  const safe = fixture('safe argv')
  const typescriptPaths = ['apps/example/has space.ts', 'apps/example/line\nname.ts', 'packages/ts/example/semi;name.ts', 'scripts/--danger.ts', 'scripts/$(touch INJECTION);.ts'].sort()
  const pythonPath = 'python/apps/example/space name.py'
  const filenames = [...typescriptPaths, pythonPath]
  for (const path of filenames) stage(safe.cwd, path)
  const indexBefore = execFileSync(realGit, ['write-tree'], { cwd: safe.cwd, encoding: 'utf8' })
  assert.equal(run(safe.cwd, safe.bin).status, 0)
  const logged = commands(safe.log)
  const lint = logged.find(args => args[0] === 'pnpm' && args[2] === 'oxlint')
  assert.deepEqual(lint?.slice(3), ['--', ...typescriptPaths])
  assert(logged.some(args => args[0] === 'uv' && args.at(-1) === pythonPath))
  assert.equal(execFileSync(realGit, ['write-tree'], { cwd: safe.cwd, encoding: 'utf8' }), indexBefore)
  passed++

  for (const command of ['pnpm', 'uv']) {
    const failing = fixture(`${command} lint failure`)
    stage(failing.cwd, command === 'pnpm' ? 'scripts/fixture.ts' : 'python/apps/example/fixture.py')
    executable(join(failing.bin, command), `#!${process.execPath}\nprocess.exit(2);\n`)
    const result = run(failing.cwd, failing.bin)
    assert.equal(result.status, 1)
    assert.match(result.stderr, /failed or is unavailable/)
    passed++
  }

  writeFileSync(join(safe.cwd, filenames[0]!), 'export const unstaged = true\n')
  const partial = run(safe.cwd, safe.bin)
  assert.equal(partial.status, 1)
  assert.match(partial.stderr, /unstaged edits/)
  assert.equal(execFileSync(realGit, ['write-tree'], { cwd: safe.cwd, encoding: 'utf8' }), indexBefore)
  writeFileSync(join(safe.cwd, filenames[0]!), 'export const fixture = true\n')
  passed++

  const outputMarker = randomBytes(24).toString('hex')
  executable(join(safe.bin, 'gitleaks'), `#!${process.execPath}\nprocess.stdout.write(${JSON.stringify(outputMarker)}); process.stderr.write(${JSON.stringify(outputMarker)}); process.exit(1);\n`)
  const blocked = run(safe.cwd, safe.bin)
  assert.equal(blocked.status, 1)
  assert(!`${blocked.stdout}${blocked.stderr}`.includes(outputMarker), 'Never relay scanner diagnostics')
  passed++

  rmSync(join(safe.bin, 'gitleaks'))
  const unavailable = run(safe.cwd, safe.bin)
  assert.equal(unavailable.status, 1)
  assert.match(unavailable.stderr, /gitleaks failed or is unavailable/)
  passed++

  const detected = fixture('actual scanner rejects synthetic credential')
  // Synthetic random fixture only; no credential file or user secret is read.
  const synthetic = randomBytes(32).toString('hex')
  stage(detected.cwd, 'apps/example/fixture.ts', `const api_key = "${synthetic}"\n`)
  executable(join(detected.bin, 'gitleaks'), `#!${process.execPath}\nconst cp = require('node:child_process'); const r = cp.spawnSync(${JSON.stringify(realScanner)}, process.argv.slice(2), {stdio:'inherit'}); process.exit(r.status ?? 1);\n`)
  const detection = run(detected.cwd, detected.bin)
  assert.equal(detection.status, 1)
  assert(!`${detection.stdout}${detection.stderr}`.includes(synthetic))
  assert(!commands(detected.log).some(args => args[0] === 'pnpm'), 'Detection must block before lint')
  passed++

  const push = fixture('push pipeline')
  assert.equal(run(push.cwd, push.bin, 'pre-push').status, 0)
  assert.deepEqual(commands(push.log).filter(args => args[0] === 'pnpm').map(args => args[2]), [
    'verify', 'typecheck:tests', 'python:lint', 'python:typecheck', 'python:test',
  ])
  passed++
  console.log(`Git hook safety: ${passed} isolated fixture checks passed; synthetic scanner output redacted.`)
} finally {
  rmSync(root, { recursive: true, force: true })
}
