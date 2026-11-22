/**
 * OAuth regression tests use temporary files and fake fetch responses. Only the
 * callback test opens a loopback HTTP listener; no Bybit request is performed.
 */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { request } from 'node:http'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { BybitOAuth, BybitTestnetOAuth } from '../dist/lib/bybit-oauth.js'
import { resolveSettings, selectCredentialPair } from '../dist/lib/host-config.js'

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
    assert.equal(authorize.pathname, '/oauth')
    assert.equal(authorize.searchParams.get('client_id'), 'ai-agent')
    assert.equal(authorize.searchParams.get('response_type'), 'code')
    assert.equal(authorize.searchParams.get('scope'), 'ai-account')
    assert.equal(authorize.searchParams.get('redirect_uri'), `http://127.0.0.1:${port}/callback`)
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
    assert.equal(existsSync(oauth.callbackFile), false)
    assert.equal(existsSync(oauth.initFile), false)
  })

  await check('AI sub-account creation enforces Bybit five-account limit', async () => {
    const oauth = new BybitTestnetOAuth(tempDirectory())
    writeJson(oauth.tokenFile, {
      access_token: 'testnet-access-fixture', refresh_token: 'testnet-refresh-fixture', expires_in: 3600,
      refresh_token_expires_in: 86_400, token_type: 'bearer', created_at: Math.floor(Date.now() / 1000), env: 'testnet',
    })
    let calls = 0
    globalThis.fetch = async (input) => {
      calls += 1
      assert.equal(String(input), 'https://api2-testnet.bybit.com/oauth/v1/resource/restrict/ai_accounts')
      return new Response(JSON.stringify({ result: { accounts: [
        { sub_member_id: '1', nickname: 'one' }, { sub_member_id: '2', nickname: 'two' },
        { sub_member_id: '3', nickname: 'three' }, { sub_member_id: '4', nickname: 'four' },
        { sub_member_id: '5', nickname: 'five' },
      ] } }), { status: 200 })
    }
    await assert.rejects(oauth.createAccount(), /at most 5 AI sub-accounts/u)
    assert.equal(calls, 1)
  })

  await check('Mainnet OAuth selects production endpoints without enabling trading', async () => {
    const directory = tempDirectory()
    const testnetTokenFile = join(directory, 'oauth-token.json')
    const testnetCredentialsFile = join(directory, 'credentials.json')
    writeJson(testnetTokenFile, { env: 'testnet', access_token: 'testnet-token-fixture' })
    writeJson(testnetCredentialsFile, { env: 'testnet', apiKey: 'testnet-key-fixture', apiSecret: 'testnet-secret-fixture' })
    const testnetTokenBefore = readFileSync(testnetTokenFile)
    const testnetCredentialsBefore = readFileSync(testnetCredentialsFile)
    const oauth = new BybitOAuth(directory, 'live')
    globalThis.fetch = async () => { throw new Error('unexpected outbound request') }
    const { authorizeUrl, port } = await oauth.start()
    assert.equal(new URL(authorizeUrl).origin, 'https://www.bybit.com')
    const init = JSON.parse(readFileSync(oauth.initFile, 'utf8')) as { state: string; verifier: string; redirectUri: string }
    assert.equal(await requestCallback(port, `state=${encodeURIComponent(init.state)}&code=code-live`), 200)
    writeJson(oauth.initFile, { ...init, state: 'state-live', verifier: 'verifier-live' })
    writeJson(oauth.callbackFile, { state: 'state-live', code: 'code-live', code_verifier: 'verifier-live' })
    let calledUrl = ''
    globalThis.fetch = async (input) => {
      calledUrl = String(input)
      const result = calledUrl.endsWith('/access_token')
        ? { access_token: 'live-access', refresh_token: 'live-refresh' }
        : { accounts: [{ sub_member_id: '123456', nickname: 'Live fixture', api_key: 'live-key-fixture', api_secret: 'live-secret-fixture' }] }
      return new Response(JSON.stringify({ result }), { status: 200 })
    }
    await oauth.exchange()
    assert.equal(calledUrl, 'https://api2.bybit.com/oauth/v1/public/access_token')
    assert.match(oauth.tokenFile, /\/live\/oauth-token\.json$/u)
    const stored = JSON.parse(readFileSync(oauth.tokenFile, 'utf8')) as Record<string, unknown>
    assert.equal(stored.env, 'live')
    await oauth.selectAccount('123456')
    const credentials = JSON.parse(readFileSync(oauth.credentialsFile, 'utf8')) as Record<string, unknown>
    assert.equal(credentials.env, 'live')
    assert.deepEqual(readFileSync(testnetTokenFile), testnetTokenBefore)
    assert.deepEqual(readFileSync(testnetCredentialsFile), testnetCredentialsBefore)
  })

  await check('Mainnet host defaults to isolated credentials and keeps live orders off', async () => {
    const previousHome = process.env.DSH_HOME
    const previousTestnetKey = process.env.BYBIT_API_KEY
    const previousTestnetSecret = process.env.BYBIT_API_SECRET
    const previousMainnetKey = process.env.BYBIT_MAINNET_API_KEY
    const previousMainnetSecret = process.env.BYBIT_MAINNET_API_SECRET
    const directory = tempDirectory()
    process.env.DSH_HOME = directory
    process.env.BYBIT_API_KEY = 'testnet-key-must-not-leak'
    process.env.BYBIT_API_SECRET = 'testnet-secret-must-not-leak'
    process.env.BYBIT_MAINNET_API_KEY = 'mainnet-key-fixture'
    process.env.BYBIT_MAINNET_API_SECRET = 'mainnet-secret-fixture'
    try {
      const testnetSettings = resolveSettings({ env: 'testnet' })
      assert.equal(testnetSettings.apiKeyEnv, 'BYBIT_API_KEY')
      assert.equal(testnetSettings.apiSecretEnv, 'BYBIT_API_SECRET')
      assert.equal(testnetSettings.fallbackApiKey, 'testnet-key-must-not-leak')
      assert.equal(testnetSettings.fallbackApiSecret, 'testnet-secret-must-not-leak')
      const settings = resolveSettings({ env: 'live' })
      assert.equal(settings.credentialsFile, join(directory, 'bybit-quant', 'live', 'credentials.json'))
      assert.equal(settings.stateFile, join(directory, 'bybit-quant', 'live', 'state.json'))
      assert.equal(settings.apiKeyEnv, 'BYBIT_MAINNET_API_KEY')
      assert.equal(settings.apiSecretEnv, 'BYBIT_MAINNET_API_SECRET')
      assert.equal(settings.fallbackApiKey, 'mainnet-key-fixture')
      assert.equal(settings.fallbackApiSecret, 'mainnet-secret-fixture')
      assert.throws(() => resolveSettings({ env: 'live', apiKeyEnv: 'BYBIT_API_KEY' }), /must not reuse Testnet variable names/)
      process.env.BYBIT_MAINNET_API_SECRET = ''
      assert.throws(() => resolveSettings({ env: 'live' }), /configured as a pair for live/)
      process.env.BYBIT_MAINNET_API_SECRET = 'mainnet-secret-fixture'
      mkdirSync(join(directory, 'bybit-quant', 'live'), { recursive: true })
      const credentialsFile = join(directory, 'bybit-quant', 'live', 'credentials.json')
      writeFileSync(credentialsFile, '{broken-json', { mode: 0o600 })
      assert.throws(() => resolveSettings({ env: 'live' }), /invalid JSON/)
      writeJson(credentialsFile, { env: 'testnet', apiKey: 'testnet-key-fixture', apiSecret: 'testnet-secret-fixture' })
      assert.throws(() => resolveSettings({ env: 'live' }), /different environment/)
      writeJson(credentialsFile, { apiKey: 'untagged-live-key', apiSecret: 'untagged-live-secret' })
      assert.throws(() => resolveSettings({ env: 'live' }), /explicit live environment marker/)
      writeJson(credentialsFile, { env: 'live', apiKey: 'one-sided-live-key' })
      assert.throws(() => resolveSettings({ env: 'live' }), /complete key pair/)
    } finally {
      if (previousHome === undefined) delete process.env.DSH_HOME
      else process.env.DSH_HOME = previousHome
      if (previousTestnetKey === undefined) delete process.env.BYBIT_API_KEY
      else process.env.BYBIT_API_KEY = previousTestnetKey
      if (previousTestnetSecret === undefined) delete process.env.BYBIT_API_SECRET
      else process.env.BYBIT_API_SECRET = previousTestnetSecret
      if (previousMainnetKey === undefined) delete process.env.BYBIT_MAINNET_API_KEY
      else process.env.BYBIT_MAINNET_API_KEY = previousMainnetKey
      if (previousMainnetSecret === undefined) delete process.env.BYBIT_MAINNET_API_SECRET
      else process.env.BYBIT_MAINNET_API_SECRET = previousMainnetSecret
    }
  })

  await check('credential selection never combines key halves across sources', async () => {
    const fallback = { apiKey: 'fallback-key', apiSecret: 'fallback-secret', source: 'credentials file' }
    assert.throws(() => selectCredentialPair('store-key', undefined, fallback), /both the API key and API secret/)
    assert.throws(() => selectCredentialPair(' ', 'store-secret', fallback), /non-empty API key pair/)
    const selected = selectCredentialPair('store-key', 'store-secret', fallback)
    assert.equal(selected.apiKey, 'store-key')
    assert.equal(selected.apiSecret, 'store-secret')
    assert.equal(selected.source, 'harness credential store')
    const preserved = selectCredentialPair(undefined, undefined, fallback)
    assert.equal(preserved.apiKey, fallback.apiKey)
    assert.equal(preserved.apiSecret, fallback.apiSecret)
    assert.equal(preserved.source, fallback.source)
  })

  await check('account selection preserves malformed and cross-environment credential files', async () => {
    const directory = tempDirectory()
    const oauth = new BybitOAuth(directory, 'live')
    mkdirSync(oauth.directory, { recursive: true })
    writeJson(oauth.tokenFile, {
      access_token: 'live-access-fixture', refresh_token: 'live-refresh-fixture', expires_in: 3600,
      refresh_token_expires_in: 86_400, token_type: 'bearer', created_at: Math.floor(Date.now() / 1000), env: 'live',
    })
    globalThis.fetch = async () => new Response(JSON.stringify({ result: {
      accounts: [{ sub_member_id: '123456', api_key: 'new-live-key-fixture', api_secret: 'new-live-secret-fixture' }],
    } }), { status: 200 })
    writeFileSync(oauth.credentialsFile, '{broken-json', { mode: 0o600 })
    const malformedBefore = readFileSync(oauth.credentialsFile)
    await assert.rejects(oauth.selectAccount('123456'), /invalid JSON/u)
    assert.deepEqual(readFileSync(oauth.credentialsFile), malformedBefore)

    writeJson(oauth.credentialsFile, { env: 'testnet', apiKey: 'existing-testnet-key', apiSecret: 'existing-testnet-secret' })
    const crossEnvironmentBefore = readFileSync(oauth.credentialsFile)
    await assert.rejects(oauth.selectAccount('123456'), /Refusing to replace a testnet credentials file/u)
    assert.deepEqual(readFileSync(oauth.credentialsFile), crossEnvironmentBefore)
  })

  await check('failed refresh preserves the existing token file byte-for-byte', async () => {
    const oauth = new BybitTestnetOAuth(tempDirectory())
    writeJson(oauth.tokenFile, {
      access_token: 'existing-access-fixture', refresh_token: 'existing-refresh-fixture', expires_in: 1,
      refresh_token_expires_in: 86_400, token_type: 'bearer', created_at: Math.floor(Date.now() / 1000) - 120, env: 'testnet',
    })
    const before = readFileSync(oauth.tokenFile)
    globalThis.fetch = async () => new Response(JSON.stringify({ retCode: 10001, retMsg: 'fixture refresh failure' }), { status: 200 })
    await assert.rejects(oauth.accounts(), /Bybit testnet OAuth failed/)
    assert.deepEqual(readFileSync(oauth.tokenFile), before)
  })

  console.log(`OAuth mock tests: ${passed} passed; no external fetch was performed`)
} finally {
  globalThis.fetch = originalFetch
  for (const directory of temporaryDirectories) rmSync(directory, { recursive: true, force: true })
}
