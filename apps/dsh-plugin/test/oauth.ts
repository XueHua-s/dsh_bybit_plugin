/**
 * OAuth regression tests use temporary files and fake fetch responses. Only the
 * callback test opens a loopback HTTP listener; no Bybit request is performed.
 */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { request } from 'node:http'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { BybitTestnetOAuth } from '../dist/lib/bybit-oauth.js'

const originalFetch = globalThis.fetch
const temporaryDirectories: string[] = []
let passed = 0

function tempDirectory(): string {
  const directory = mkdtempSync(join(tmpdir(), 'bybit-oauth-test-'))
  temporaryDirectories.push(directory)
  return directory
}

async function check(label: string, run: () => Promise<void>): Promise<void> {
  await run()
  passed += 1
  console.log(`ok ${label}`)
}

async function requestCallback(port: number, query: string): Promise<number> {
  return new Promise((resolve, reject) => {
    const callback = request({ host: '127.0.0.1', port, path: `/callback?${query}` }, (response) => {
      response.resume()
      response.once('end', () => resolve(response.statusCode ?? 0))
    })
    callback.once('error', reject)
    callback.end()
  })
}

function writeJson(path: string, value: unknown): void {
  writeFileSync(path, `${JSON.stringify(value)}\n`, { mode: 0o600 })
}

try {
  await check('PKCE challenge and state mismatch stay local', async () => {
    const oauth = new BybitTestnetOAuth(tempDirectory())
    globalThis.fetch = async () => { throw new Error('unexpected outbound request') }
    const { authorizeUrl, port } = await oauth.start()
    const authorize = new URL(authorizeUrl)
    const init = JSON.parse(readFileSync(oauth.initFile, 'utf8')) as { state: string; verifier: string }
    const challenge = createHash('sha256').update(init.verifier).digest('base64url')
    assert.equal(authorize.origin, 'https://testnet.bybit.com')
    assert.equal(authorize.searchParams.get('code_challenge_method'), 'S256')
    assert.equal(authorize.searchParams.get('code_challenge'), challenge)
    assert.equal(authorize.searchParams.get('state'), init.state)
    assert.equal(await requestCallback(port, 'state=wrong&code=ignored'), 403)
    await assert.rejects(oauth.exchange(), /OAuth callback validation failed/)
    assert.deepEqual(JSON.parse(readFileSync(oauth.callbackFile, 'utf8')), { error: 'state_mismatch' })
  })

  await check('exchange uses isolated Testnet configuration without a secret', async () => {
    const oauth = new BybitTestnetOAuth(tempDirectory())
    writeJson(oauth.initFile, { state: 'state-fixture', verifier: 'verifier-fixture', redirectUri: 'http://127.0.0.1:9876/callback' })
    writeJson(oauth.callbackFile, { state: 'state-fixture', code: 'code-fixture', code_verifier: 'verifier-fixture' })
    let calledUrl = ''
    let requestBody = ''
    globalThis.fetch = async (input, init) => {
      calledUrl = String(input)
      requestBody = String(init?.body ?? '')
      return new Response(JSON.stringify({ result: { access_token: 'access-fixture', refresh_token: 'refresh-fixture' } }), { status: 200 })
    }
    await oauth.exchange()
    const params = new URLSearchParams(requestBody)
    assert.equal(calledUrl, 'https://api2-testnet.bybit.com/oauth/v1/public/access_token')
    assert.equal(params.get('client_id'), 'ai-agent')
    assert.equal(params.get('code'), 'code-fixture')
    assert.equal(params.get('code_verifier'), 'verifier-fixture')
    assert.equal([...params.keys()].sort().join(','), 'client_id,code,code_verifier')
    const stored = JSON.parse(readFileSync(oauth.tokenFile, 'utf8')) as Record<string, unknown>
    assert.equal(stored.env, 'testnet')
    assert.equal(stored.access_token, 'access-fixture')
  })

  await check('failed refresh preserves the existing token file byte-for-byte', async () => {
    const oauth = new BybitTestnetOAuth(tempDirectory())
    writeJson(oauth.tokenFile, {
      access_token: 'existing-access-fixture', refresh_token: 'existing-refresh-fixture', expires_in: 1,
      refresh_token_expires_in: 86_400, token_type: 'bearer', created_at: Math.floor(Date.now() / 1000) - 120, env: 'testnet',
    })
    const before = readFileSync(oauth.tokenFile)
    globalThis.fetch = async () => new Response(JSON.stringify({ retCode: 10001, retMsg: 'fixture refresh failure' }), { status: 200 })
    await assert.rejects(oauth.accounts(), /Bybit Testnet OAuth failed/)
    assert.deepEqual(readFileSync(oauth.tokenFile), before)
  })

  console.log(`OAuth mock tests: ${passed} passed; no external fetch was performed`)
} finally {
  globalThis.fetch = originalFetch
  for (const directory of temporaryDirectories) rmSync(directory, { recursive: true, force: true })
}
