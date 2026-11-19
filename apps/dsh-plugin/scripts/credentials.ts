#!/usr/bin/env node
/**
 * Write Bybit API credentials without putting them in a chat, a shell history,
 * or the profile patch.
 *
 * Copy the value in the Bybit console, then run:
 *
 *   pnpm run credentials -- key        # reads the clipboard into apiKey
 *   pnpm run credentials -- secret     # reads the clipboard into apiSecret
 *   pnpm run credentials -- status     # shows what is configured (masked)
 *   pnpm run credentials -- clear      # removes both values
 *   pnpm run credentials -- key --stdin
 *
 * The file is created with mode 600 under $DSH_HOME/bybit-quant/credentials.json,
 * the same path the plugin reads when the profile config has no apiKey/apiSecret.
 */
import { execFileSync } from 'node:child_process'
import { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'

const home = process.env.DSH_HOME !== undefined && process.env.DSH_HOME !== '' ? process.env.DSH_HOME : join(homedir(), '.dsh')
const file = join(home, 'bybit-quant', 'credentials.json')
const argumentsList = process.argv.slice(2).filter(value => value !== '--')
const field = argumentsList[0]
const useStdin = argumentsList.includes('--stdin')

interface CredentialsDocument {
  apiKey?: string
  apiSecret?: string
  env?: string
}

/** Read the current document, tolerating a missing or malformed file. */
function read(): CredentialsDocument {
  try {
    if (!existsSync(file)) return {}
    const parsed = JSON.parse(readFileSync(file, 'utf8'))
    return typeof parsed === 'object' && parsed !== null ? parsed : {}
  } catch {
    return {}
  }
}

/** Persist with owner-only permissions. */
function write(document: CredentialsDocument): void {
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, `${JSON.stringify(document, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 })
  chmodSync(file, 0o600)
}

/** Clipboard on macOS, or stdin for other platforms and scripts. */
function readValue() {
  if (useStdin) {
    return readFileSync(0, 'utf8').trim()
  }
  try {
    return execFileSync('pbpaste', { encoding: 'utf8' }).trim()
  } catch {
    console.error('cannot read the clipboard here; copy the value and rerun with --stdin < value')
    process.exit(1)
  }
}

/** Show only the tail so a screenshot of the terminal is harmless. */
function mask(value: unknown): string {
  if (typeof value !== 'string' || value === '') return '(empty)'
  if (value.length <= 4) return '****'
  return `${'*'.repeat(Math.min(value.length - 4, 10))}${value.slice(-4)}`
}

const document = read()

if (field === undefined || field === 'status') {
  console.log(`file     ${file}`)
  console.log(`apiKey   ${mask(document.apiKey)}`)
  console.log(`apiSecret${typeof document.apiSecret === 'string' && document.apiSecret !== '' ? ' set' : ' (empty)'}`)
  console.log(`env      ${typeof document.env === 'string' ? document.env : '(not set; the plugin config decides)'}`)
  process.exit(0)
}

if (field === 'clear') {
  write({})
  console.log('credentials cleared')
  process.exit(0)
}

if (field !== 'key' && field !== 'secret') {
  console.error('usage: pnpm run credentials -- key|secret|status|clear [--stdin]')
  process.exit(1)
}

const value = readValue()
if (value === '') {
  console.error('the value is empty; nothing written')
  process.exit(1)
}
if (/\s/.test(value)) {
  console.error('the value contains whitespace; copy only the key or secret itself')
  process.exit(1)
}

if (field === 'key') document.apiKey = value
else document.apiSecret = value

write(document)
console.log(`${field} written (${mask(value)}) to ${file}`)
