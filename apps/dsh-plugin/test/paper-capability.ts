import assert from 'node:assert/strict'
import { chmodSync, lstatSync, mkdirSync, mkdtempSync, renameSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import { createServer } from 'node:net'
import type { Socket } from 'node:net'
import { join } from 'node:path'
import { createPaperCapabilityProvider, paperConfiguration } from '../src/lib/paper-capability.ts'

process.env = {}
const root = mkdtempSync(`${process.platform === 'darwin' ? '/private/tmp' : '/tmp'}/bqph-`)
chmodSync(root, 0o700)
const origin = 'http://127.0.0.1:8766'
const sessionId = 'paper-test'
const token = 'synthetic-paper-provider-0123456789-"\\'
const golden = '{"version":1,"environment":"internal_paper","session_id":"paper-test","origin":"http://127.0.0.1:8766"}\n'
const response = (extra: Record<string, unknown> = {}) => JSON.stringify({ version: 1, environment: 'internal_paper', session_id: sessionId, origin, capability: token, ...extra }) + '\n'
let sequence = 0
let assertions = 0
const providers: ReturnType<typeof createPaperCapabilityProvider>[] = []
const cleanups: Array<() => Promise<void>> = []
type Handler = (socket: Socket, request: Buffer) => void

async function broker(handler: Handler) {
  const directory = join(root, `p${++sequence}`)
  mkdirSync(directory, { mode: 0o700 })
  const socketPath = join(directory, 's')
  const sockets = new Set<Socket>()
  let connections = 0
  const server = createServer({ allowHalfOpen: true }, socket => {
    connections++
    sockets.add(socket)
    socket.on('error', () => {})
    socket.on('close', () => sockets.delete(socket))
    const chunks: Buffer[] = []
    socket.on('data', chunk => chunks.push(chunk))
    socket.on('end', () => handler(socket, Buffer.concat(chunks)))
  })
  await new Promise<void>((resolve, reject) => { server.once('error', reject); server.listen(socketPath, resolve) })
  chmodSync(socketPath, 0o600)
  const provider = createPaperCapabilityProvider({ socketPath, origin, sessionId })
  providers.push(provider)
  let closed = false
  const close = async () => {
    if (closed) return
    closed = true
    provider.close()
    for (const socket of sockets) socket.destroy()
    await new Promise<void>(resolve => server.close(() => resolve()))
  }
  cleanups.push(close)
  return {
    provider, socketPath, directory, server, sockets,
    get connections() { return connections },
    close,
  }
}

async function unavailable(provider: ReturnType<typeof createPaperCapabilityProvider>) {
  let safe = false
  try { await provider.resolve() } catch (error: unknown) {
    safe = error instanceof Error && error.message === 'capability_unavailable' && !String(error).includes(token)
  }
  assert.ok(safe, 'provider failure must contain only its fixed code')
  assertions++
}

try {
  assert.equal(paperConfiguration({}), undefined)
  assert.equal(paperConfiguration({ paperControlEnabled: false }), undefined)
  for (const config of [
    { paperSessionId: sessionId }, { paperCapabilitySocket: '/private/tmp/s' }, { paperControlEnabled: true },
    { paperControlEnabled: 'true' }, { paperSessionId: '_bad', paperCapabilitySocket: join(root, 's') },
    ...['http://localhost:8766', 'http://127.1:8766', 'http://127.0.0.1:8766/', 'https://127.0.0.1:8766', 'http://127.0.0.1:80', 'http://127.0.0.1:8766/?x=1']
      .map(paperBaseUrl => ({ paperSessionId: sessionId, paperCapabilitySocket: join(root, 's'), paperBaseUrl })),
    ...['relative/s', `${root}//s`, `${root}/../s`, `${root}/s/`, `${root}/a\0b`, `${root}/${'x'.repeat(100)}`]
      .map(paperCapabilitySocket => ({ paperSessionId: sessionId, paperCapabilitySocket })),
  ]) assert.throws(() => paperConfiguration(config), /^Error: invalid_config$/u)
  assertions++
  const valid = await broker((socket, request) => {
    assert.equal(request.toString(), golden, 'request uses canonical golden bytes and EOF')
    const wire = response()
    socket.write(wire.slice(0, 35))
    setTimeout(() => socket.end(wire.slice(35)), 15)
  })
  assert.ok((await valid.provider.resolve()) === token, 'split canonical response resolves privately')
  assert.ok((await valid.provider.resolve()) === token, 'each operation resolves a fresh capability')
  assert.equal(valid.connections, 2)
  assert.deepEqual(Object.keys(valid.provider).sort(), ['close', 'resolve'])
  await valid.close()
  await unavailable(valid.provider)
  assertions++

  for (const wire of [
    response({ version: 2 }), response({ environment: 'testnet' }), response({ session_id: 'wrong' }),
    response({ origin: 'http://127.0.0.1:8767' }), response({ extra: true }), response({ capability: 'short' }),
    response().replace('{', '{ '), response().trimEnd(), response() + '\n',
    response().replace('"version":1', '"version":1,"version":1'),
    response().replace('"paper-test"', '"paper-\\u0074est"'), '{"invalid":true}\n', 'x'.repeat(1025),
  ]) {
    const invalid = await broker(socket => socket.end(wire))
    await unavailable(invalid.provider)
    await invalid.close()
  }
  const delayed = await broker(socket => {
    socket.write(response())
    setTimeout(() => socket.end('{}\n'), 25)
  })
  await unavailable(delayed.provider)
  await delayed.close()

  const stalled = await broker(socket => socket.write(response()))
  const started = performance.now()
  await unavailable(stalled.provider)
  assert.ok(performance.now() - started >= 400 && performance.now() - started < 1500, 'response without EOF uses total deadline')
  await stalled.close()

  const saturated = await broker(() => {})
  const pending = Array.from({ length: 4 }, () => unavailable(saturated.provider))
  await unavailable(saturated.provider)
  await new Promise<void>(resolve => setTimeout(resolve, 30))
  assert.equal(saturated.connections, 4, 'fifth operation is refused without a queue or socket')
  saturated.provider.close()
  await Promise.all(pending)
  await unavailable(saturated.provider)
  await saturated.close()

  const mutable = await broker(socket => { chmodSync(mutable.directory, 0o755); socket.end(response()) })
  await unavailable(mutable.provider)
  chmodSync(mutable.directory, 0o700)
  await mutable.close()
  const swapped = await broker(socket => {
    renameSync(swapped.directory, `${swapped.directory}-old`)
    mkdirSync(swapped.directory, { mode: 0o700 })
    socket.end(response())
  })
  await unavailable(swapped.provider)
  await swapped.close()
  assert.ok(lstatSync(`${swapped.directory}-old`).isDirectory(), 'provider never deletes operator directories')

  for (const kind of ['directory-mode', 'socket-mode', 'socket-link', 'parent-link', 'regular-file'] as const) {
    const unsafe = await broker(socket => socket.end(response()))
    let path = unsafe.socketPath
    if (kind === 'directory-mode') chmodSync(unsafe.directory, 0o770)
    if (kind === 'socket-mode') chmodSync(path, 0o666)
    if (kind === 'socket-link') { path = join(unsafe.directory, 'link'); symlinkSync(unsafe.socketPath, path) }
    if (kind === 'parent-link') { symlinkSync(unsafe.directory, `${unsafe.directory}-link`); path = join(`${unsafe.directory}-link`, 's') }
    if (kind === 'regular-file') { path = join(unsafe.directory, 'file'); writeFileSync(path, '', { mode: 0o600 }) }
    const provider = createPaperCapabilityProvider({ socketPath: path, origin, sessionId })
    providers.push(provider)
    await unavailable(provider)
    assert.equal(unsafe.connections, 0, 'unsafe path fails before connect')
    chmodSync(unsafe.directory, 0o700)
    await unsafe.close()
  }
  console.log(`ok paper capability: ${assertions} bounded private IPC assertions; canonical EOF, scope/path/inode checks, saturation, close and safe failures`)
} finally {
  for (const provider of providers) provider.close()
  await Promise.all(cleanups.map(close => close()))
  rmSync(root, { recursive: true, force: true })
}
