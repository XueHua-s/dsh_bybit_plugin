import { lstatSync } from 'node:fs'
import type { Stats } from 'node:fs'
import { Socket } from 'node:net'
import { dirname, isAbsolute, parse, resolve } from 'node:path'

type Scope = { socketPath: string, origin: string, sessionId: string }
export type PaperConfiguration = Scope & { controlEnabled: boolean }
const ID = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/u
const MAX_BYTES = 1024
const DEADLINE_MS = 500

function invalid(): never { throw new Error('invalid_config') }

/** Canonical numeric loopback authority only; never an exchange or browser destination. */
function originOf(value: unknown): string {
  if (typeof value !== 'string') return invalid()
  try {
    const url = new URL(value)
    if (url.origin !== value || url.protocol !== 'http:' || url.username || url.password
      || !(url.hostname === '[::1]' || /^127(?:\.\d{1,3}){3}$/u.test(url.hostname))) return invalid()
    return url.origin
  } catch { return invalid() }
}

function socketPathOf(value: unknown): string {
  if (typeof value !== 'string' || !isAbsolute(value) || resolve(value) !== value
    || value.includes('\0') || Buffer.byteLength(value) > 100 || dirname(value) === parse(value).root) return invalid()
  return value
}

/** Validate paper settings before legacy settings can inspect unrelated credentials. */
export function paperConfiguration(config: Record<string, unknown>): PaperConfiguration | undefined {
  if (config.paperControlEnabled !== undefined && typeof config.paperControlEnabled !== 'boolean') return invalid()
  const present = ['paperCapabilitySocket', 'paperSessionId', 'paperBaseUrl'].some(key => config[key] !== undefined)
  if (!present && config.paperControlEnabled !== true) return undefined
  if (typeof config.paperSessionId !== 'string' || !ID.test(config.paperSessionId)) return invalid()
  return {
    socketPath: socketPathOf(config.paperCapabilitySocket),
    origin: originOf(config.paperBaseUrl ?? 'http://127.0.0.1:8766'),
    sessionId: config.paperSessionId,
    controlEnabled: config.paperControlEnabled === true,
  }
}

type PathIdentity = { path: string, stat: Stats }
function failure(): Error { return new Error('capability_unavailable') }

/** No symlink is trusted, including ancestors; only the dedicated parent may hold the socket. */
function inspectPath(path: string): PathIdentity[] {
  const uid = process.getuid?.()
  if (uid === undefined || process.platform === 'win32') throw failure()
  const chain: string[] = []
  for (let current = dirname(path);; current = dirname(current)) {
    chain.unshift(current)
    if (current === parse(current).root) break
  }
  const identities = chain.map(current => {
    const stat = lstatSync(current)
    const temporary = (current === '/private/tmp' || current === '/tmp') && stat.uid === 0 && (stat.mode & 0o1000) !== 0
    if (!stat.isDirectory() || stat.isSymbolicLink() || ![0, uid].includes(stat.uid)
      || ((stat.mode & 0o022) !== 0 && !temporary)) throw failure()
    if (current === dirname(path) && (stat.uid !== uid || (stat.mode & 0o7777) !== 0o700)) throw failure()
    return { path: current, stat }
  })
  const stat = lstatSync(path)
  if (!stat.isSocket() || stat.isSymbolicLink() || stat.uid !== uid || (stat.mode & 0o7777) !== 0o600) throw failure()
  return [...identities, { path, stat }]
}

function unchanged(before: PathIdentity[], path: string): void {
  const after = inspectPath(path)
  if (after.length !== before.length || before.some((value, index) => {
    const next = after[index]
    return next === undefined || value.path !== next.path || value.stat.dev !== next.stat.dev
      || value.stat.ino !== next.stat.ino || value.stat.uid !== next.stat.uid || value.stat.mode !== next.stat.mode
  })) throw failure()
}

/** Owns private IPC trust, canonical framing and socket lifetime. No token is cached or exported as state. */
export function createPaperCapabilityProvider(scope: Scope): { resolve(): Promise<string>, close(): void } {
  const socketPath = socketPathOf(scope.socketPath)
  const origin = originOf(scope.origin)
  if (!ID.test(scope.sessionId)) return invalid()
  const sessionId = scope.sessionId
  const frame = JSON.stringify({ version: 1, environment: 'internal_paper', session_id: sessionId, origin }) + '\n'
  const sockets = new Map<Socket, () => void>()
  let closed = false
  return {
    close() {
      closed = true
      for (const stop of sockets.values()) stop()
    },
    resolve() {
      if (closed || sockets.size >= 4) return Promise.reject(failure())
      return new Promise<string>((accept, reject) => {
        const socket = new Socket({ allowHalfOpen: true })
        const started = performance.now()
        const chunks: Buffer[] = []
        let bytes = 0
        let settled = false
        const finish = (capability?: string) => {
          if (settled) return
          settled = true
          clearTimeout(timer)
          sockets.delete(socket)
          socket.destroy()
          if (capability === undefined) reject(failure())
          else accept(capability)
        }
        const timer = setTimeout(() => finish(), DEADLINE_MS)
        sockets.set(socket, () => finish())
        socket.on('error', () => finish())
        socket.on('close', () => finish())
        try {
          const identity = inspectPath(socketPath)
          if (performance.now() - started >= DEADLINE_MS) { finish(); return }
          socket.on('connect', () => {
            try { unchanged(identity, socketPath); socket.end(frame) } catch { finish() }
          })
          socket.on('data', (chunk: Buffer) => {
            bytes += chunk.length
            if (bytes > MAX_BYTES) finish()
            else chunks.push(chunk)
          })
          // First LF is not completion: delayed trailing frames must also be rejected.
          socket.on('end', () => {
            try {
              if (settled || closed || performance.now() - started >= DEADLINE_MS) { finish(); return }
              const received = Buffer.concat(chunks)
              const value: unknown = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(received))
              if (value === null || typeof value !== 'object' || Array.isArray(value)) throw failure()
              const fields = value as Record<string, unknown>
              const capability = fields.capability
              if (fields.version !== 1 || fields.environment !== 'internal_paper' || fields.session_id !== sessionId
                || fields.origin !== origin || typeof capability !== 'string' || !/^[\x21-\x7e]{32,128}$/u.test(capability)) throw failure()
              const canonical = JSON.stringify({ version: 1, environment: 'internal_paper', session_id: sessionId, origin, capability }) + '\n'
              if (!received.equals(Buffer.from(canonical))) throw failure()
              unchanged(identity, socketPath)
              finish(capability)
            } catch { finish() }
          })
          socket.connect(socketPath)
        } catch { finish() }
      })
    },
  }
}
