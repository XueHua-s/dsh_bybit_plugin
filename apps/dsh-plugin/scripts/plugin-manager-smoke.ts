#!/usr/bin/env node
/**
 * Disposable official DSH Plugin Manager lifecycle smoke.
 *
 * This script deliberately uses a temporary DSH_HOME and a local packed
 * artifact. It never edits a managed profile, reads credential contents, or
 * contacts an exchange. A missing DSH CLI is an explicit external blocker,
 * not a simulated pass.
 */
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import { homedir, tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import { pnpmEnvironment } from './pnpm-environment.ts'

const root = resolve(decodeURIComponent(new URL('..', import.meta.url).pathname))
const packageName = '@bybit-quant/dsh-plugin'
const tempHome = mkdtempSync(join(tmpdir(), 'bybit-dsh-plugin-smoke-'))
const userState = join(tempHome, 'bybit-quant')
const stateFiles: Array<readonly [string, string]> = [
  ['credentials.testnet', 'synthetic-testnet-credential-sentinel'],
  ['state.json', '{"paper":{"balanceUsd":10000,"history":["fixture"]}}'],
  ['strategy-config.json', '{"version":1,"strategy":"fixture"}'],
]

function sha256(path: string): string {
  return createHash('sha256').update(readFileSync(path)).digest('hex')
}

function stateHashes(): Record<string, string> {
  return Object.fromEntries(stateFiles.map(([name]) => [name, sha256(join(userState, name))]))
}

function command(binary: string, args: string[], label: string): string {
  const result = spawnSync(binary, args, {
    cwd: root,
    encoding: 'utf8',
    env: { ...process.env, DSH_HOME: tempHome },
  })
  if (result.status !== 0) {
    const detail = `${result.stderr ?? ''}`.trim().split('\n').slice(-3).join(' ')
    throw new Error(`${label} failed (exit ${result.status ?? 'unknown'})${detail === '' ? '' : `: ${detail}`}`)
  }
  return `${result.stdout ?? ''}`
}

function findDsh(): string | undefined {
  const candidates = [
    process.env.DSH_BIN,
    join(homedir(), 'Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh'),
    '/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh',
  ].filter((value): value is string => typeof value === 'string' && value !== '')
  for (const candidate of candidates) if (existsSync(candidate)) return candidate
  const probe = spawnSync('sh', ['-lc', 'command -v dsh'], { encoding: 'utf8' })
  const path = `${probe.stdout ?? ''}`.trim()
  return path === '' ? undefined : path
}

function packArtifact(): string {
  const packedDir = mkdtempSync(join(tempHome, 'packed-'))
  const result = spawnSync('pnpm', ['pack', '--pack-destination', packedDir], {
    cwd: root,
    encoding: 'utf8',
    env: pnpmEnvironment(),
  })
  if (result.status !== 0) throw new Error(`pnpm pack failed: ${(result.stderr ?? '').trim()}`)
  const archive = readdirSync(packedDir).find(file => file.endsWith('.tgz'))
  if (archive === undefined) throw new Error('pnpm pack produced no archive')
  return join(packedDir, archive)
}

/** Build a second local archive without changing the checked-in package version. */
function packUpgradeArtifact(sourceArchive: string): { archive: string, previousVersion: string, version: string } {
  const stage = mkdtempSync(join(tempHome, 'upgrade-stage-'))
  const extract = spawnSync('tar', ['-xzf', sourceArchive, '-C', stage], { encoding: 'utf8' })
  if (extract.status !== 0) throw new Error(`tar extract failed: ${(extract.stderr ?? '').trim()}`)
  const packageDir = join(stage, 'package')
  const packageFile = join(packageDir, 'package.json')
  const manifest = JSON.parse(readFileSync(packageFile, 'utf8')) as Record<string, unknown>
  const currentVersion = manifest.version
  if (typeof currentVersion !== 'string' || !/^\d+\.\d+\.\d+$/u.test(currentVersion)) {
    throw new Error('packed Bundle has no semver version')
  }
  const parts = currentVersion.split('.')
  const major = parts[0]
  const minor = parts[1]
  const patch = Number(parts[2])
  if (major === undefined || minor === undefined || !Number.isSafeInteger(patch) || patch < 0 || patch >= Number.MAX_SAFE_INTEGER) {
    throw new Error('packed Bundle version cannot be incremented safely')
  }
  const version = `${major}.${minor}.${patch + 1}`
  writeFileSync(packageFile, `${JSON.stringify({ ...manifest, version }, null, 2)}\n`)
  const packedDir = mkdtempSync(join(tempHome, 'packed-upgrade-'))
  const result = spawnSync('pnpm', ['pack', '--pack-destination', packedDir, '--dir', packageDir], {
    cwd: root,
    encoding: 'utf8',
    env: pnpmEnvironment(),
  })
  if (result.status !== 0) throw new Error(`pnpm pack upgrade failed: ${(result.stderr ?? '').trim()}`)
  const archive = readdirSync(packedDir).find(file => file.endsWith('.tgz'))
  if (archive === undefined) throw new Error('pnpm pack upgrade produced no archive')
  return { archive: join(packedDir, archive), previousVersion: currentVersion, version }
}

function installedVersion(): string {
  const manifest = join(tempHome, 'profiles', 'sdk', 'node_modules', '@bybit-quant', 'dsh-plugin', 'package.json')
  const value = JSON.parse(readFileSync(manifest, 'utf8')) as Record<string, unknown>
  if (typeof value.version !== 'string') throw new Error('installed Bundle version is missing')
  return value.version
}

function main(): void {
  const dsh = findDsh()
  if (dsh === undefined) {
    console.error('BLOCKED: official DSH CLI was not found; set DSH_BIN to run this smoke.')
    process.exitCode = 2
    return
  }
  mkdirSync(userState, { recursive: true, mode: 0o700 })
  for (const [name, contents] of stateFiles) writeFileSync(join(userState, name), contents, { mode: 0o600 })
  const before = stateHashes()
  const archive = packArtifact()
  const upgrade = packUpgradeArtifact(archive)
  const dshVersion = command(dsh, ['--version'], 'dsh --version').trim().split('\n').at(-1) ?? 'unknown'
  command(dsh, ['plugin', '--profile', 'sdk', 'add', archive], 'plugin install')
  const installedConfig = command(dsh, ['--profile', 'sdk', '--dump-config'], 'installed profile inspection')
  if (!installedConfig.includes(packageName)) throw new Error('official CLI reported success but the disposable profile does not select the Bundle')
  const installed = installedVersion()
  if (installed !== upgrade.previousVersion) throw new Error(`unexpected installed Bundle version: ${installed}`)
  command(dsh, ['plugin', '--profile', 'sdk', 'add', upgrade.archive], 'plugin upgrade')
  const upgradedConfig = command(dsh, ['--profile', 'sdk', '--dump-config'], 'upgraded profile inspection')
  if (!upgradedConfig.includes(packageName)) throw new Error('upgraded profile no longer selects the Bundle')
  const upgraded = installedVersion()
  if (upgraded !== upgrade.version) throw new Error(`Bundle upgrade did not install ${upgrade.version}`)
  const afterUpgrade = stateHashes()
  if (JSON.stringify(before) !== JSON.stringify(afterUpgrade)) throw new Error('user-owned state changed across install/upgrade')
  command(dsh, ['plugin', '--profile', 'sdk', 'remove', packageName], 'plugin uninstall')
  const removedConfig = command(dsh, ['--profile', 'sdk', '--dump-config'], 'removed profile inspection')
  if (removedConfig.includes(packageName)) throw new Error('Bundle remains selected in the disposable profile after uninstall')
  const after = stateHashes()
  if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error('user-owned state changed across install/remove')
  console.log(JSON.stringify({ ok: true, dshVersion, package: packageName, lifecycle: ['install', 'upgrade', 'remove'], versions: { installed, upgraded }, selectedAfterInstall: true, selectedAfterUpgrade: true, selectedAfterUninstall: false, statePreserved: true, exchangeRequests: 0, dshHome: '<temporary>' }))
}

try {
  main()
} finally {
  rmSync(tempHome, { recursive: true, force: true })
}
