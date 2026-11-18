import { randomUUID } from 'node:crypto'
import { spawn } from 'node:child_process'

export interface SandboxOptions {
  code: string
  timeoutMs?: number
  memoryMb?: number
}

export interface SandboxResult {
  ok: boolean
  output: string
  error?: string
  timedOut: boolean
}

// Keep the runtime immutable across hosts. Refresh this digest only through a
// reviewed dependency update that records the registry evidence in SDD.
export const SANDBOX_IMAGE = 'node:22.20.0-alpine@sha256:dbcedd8aeab47fbc0f4dd4bffa55b7c3c729a707875968d467aaaea42d6225af'
const OUTPUT_LIMIT = 100_000
const ERROR_LIMIT = 10_000
const RUNNER = [
  'const fs = await import("node:fs");',
  'const source = fs.readFileSync(0, "utf8");',
  'const candidate = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);',
  'const value = typeof candidate.default === "function" ? await candidate.default() : candidate.result;',
  'process.stdout.write(JSON.stringify(value ?? null));',
  'process.exit(0);',
].join('\n')

/** Run untrusted research code in a credential-free, network-disabled container. */
export async function runAlgorithmSandbox({ code, timeoutMs = 5000, memoryMb = 256 }: SandboxOptions): Promise<SandboxResult> {
  if (typeof code !== 'string' || code.length === 0 || code.length > 200_000) {
    throw new Error('sandbox code must be a non-empty string under 200 KB')
  }
  const timeout = Math.min(Math.max(Math.trunc(timeoutMs), 100), 60_000)
  const memory = Math.min(Math.max(Math.trunc(memoryMb), 64), 2048)
  return execute({ code, timeoutMs: timeout, memoryMb: memory })
}

function execute({ code, timeoutMs, memoryMb }: { code: string, timeoutMs: number, memoryMb: number }): Promise<SandboxResult> {
  const name = `bybit-quant-sandbox-${randomUUID()}`
  const args = [
    'run', '--rm', '--interactive', '--name', name,
    '--network=none', '--read-only', '--memory', `${memoryMb}m`, '--cpus=1', '--pids-limit=32',
    '--security-opt=no-new-privileges', '--cap-drop=ALL', '--user=65532:65532',
    '--tmpfs', '/tmp:rw,noexec,nosuid,size=16m',
    SANDBOX_IMAGE, 'node', '-e', RUNNER,
  ]
  return new Promise((resolve) => {
    const child = spawn('docker', args, {
      env: { PATH: process.env.PATH ?? '' },
      stdio: ['pipe', 'pipe', 'pipe'],
    })
    const output = new BoundedOutputCapture(OUTPUT_LIMIT * 4)
    const errors = new BoundedOutputCapture(ERROR_LIMIT * 4)
    let timedOut = false
    let settled = false
    child.stdout.on('data', chunk => output.append(chunk))
    child.stderr.on('data', chunk => errors.append(chunk))
    child.once('error', error => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      resolve({ ok: false, output: '', error: error.message, timedOut: false })
    })
    child.once('close', codeValue => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      const stdout = output.toString().slice(0, OUTPUT_LIMIT)
      const stderr = errors.toString().slice(0, ERROR_LIMIT)
      resolve({ ok: codeValue === 0, output: stdout, ...(stderr === '' ? {} : { error: stderr }), timedOut })
    })
    child.stdin.end(code)
    const timer = setTimeout(() => {
      timedOut = true
      const killer = spawn('docker', ['kill', name], { stdio: 'ignore', env: { PATH: process.env.PATH ?? '' } })
      killer.unref()
    }, timeoutMs)
  })
}

/** Retain a fixed byte budget while continuing to drain the child stream. */
export class BoundedOutputCapture {
  private readonly byteLimit: number
  private readonly storage: Buffer
  private retainedBytes = 0

  constructor(byteLimit: number) {
    if (!Number.isSafeInteger(byteLimit) || byteLimit < 0) {
      throw new Error('output byte limit must be a non-negative safe integer')
    }
    this.byteLimit = byteLimit
    this.storage = Buffer.allocUnsafe(byteLimit)
  }

  append(value: Buffer | string): void {
    const remaining = this.byteLimit - this.retainedBytes
    if (remaining <= 0) return
    const chunk = Buffer.isBuffer(value) ? value : Buffer.from(value)
    const retainedBytes = Math.min(chunk.length, remaining)
    if (retainedBytes === 0) return
    chunk.copy(this.storage, this.retainedBytes, 0, retainedBytes)
    this.retainedBytes += retainedBytes
  }

  toString(): string {
    return this.storage.subarray(0, this.retainedBytes).toString('utf8')
  }

  get size(): number {
    return this.retainedBytes
  }
}
