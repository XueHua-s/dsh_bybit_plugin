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

const IMAGE = 'node:22.20.0-alpine'
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
    IMAGE, 'node', '-e', RUNNER,
  ]
  return new Promise((resolve) => {
    const child = spawn('docker', args, {
      env: { PATH: process.env.PATH ?? '' },
      stdio: ['pipe', 'pipe', 'pipe'],
    })
    const output: Buffer[] = []
    const errors: Buffer[] = []
    let timedOut = false
    let settled = false
    child.stdout.on('data', chunk => output.push(Buffer.from(chunk)))
    child.stderr.on('data', chunk => errors.push(Buffer.from(chunk)))
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
      const stdout = Buffer.concat(output).toString('utf8').slice(0, 100_000)
      const stderr = Buffer.concat(errors).toString('utf8').slice(0, 10_000)
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
