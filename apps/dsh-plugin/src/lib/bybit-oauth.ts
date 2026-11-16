import { createHash, randomBytes } from 'node:crypto'
import { chmod, mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'
import { createServer } from 'node:http'

const CLIENT_ID = 'ai-agent'
const AUTH_BASE = 'https://testnet.bybit.com'
const API_BASE = 'https://api2-testnet.bybit.com'
const CALLBACK_HOST = '127.0.0.1'
const CALLBACK_PATH = '/callback'
const CALLBACK_PORT_START = 9876

type OAuthToken = {
  access_token: string
  refresh_token: string
  expires_in: number
  refresh_token_expires_in: number
  token_type: string
  created_at: number
  env: 'testnet'
}

type OAuthCallback = { code: string; state: string; code_verifier: string }
type OAuthResponse = { retCode?: number; ret_code?: number; retMsg?: string; ret_msg?: string; result?: unknown } & Record<string, unknown>

export interface AiAccountSummary { sub_member_id: string; nickname: string }

/** Keeps Testnet authorization, token exchange, and credential storage off the Harness profile. */
export class BybitTestnetOAuth {
  readonly directory: string
  readonly callbackFile: string
  readonly initFile: string
  readonly tokenFile: string
  readonly credentialsFile: string

  constructor(directory = join(process.env.DSH_HOME || join(homedir(), '.dsh'), 'bybit-quant')) {
    this.directory = directory
    this.callbackFile = join(directory, 'oauth-callback.json')
    this.initFile = join(directory, 'oauth-init.json')
    this.tokenFile = join(directory, 'oauth-token.json')
    this.credentialsFile = join(directory, 'credentials.json')
  }

  /** Starts a loopback PKCE callback and returns a Testnet-only authorization URL. */
  async start(): Promise<{ authorizeUrl: string; port: number }> {
    await mkdir(this.directory, { recursive: true, mode: 0o700 })
    await chmod(this.directory, 0o700)
    await rm(this.callbackFile, { force: true })
    const verifier = randomBytes(32).toString('base64url')
    const challenge = createHash('sha256').update(verifier).digest('base64url')
    const state = randomBytes(24).toString('base64url')
    const { server, port } = await this.listen(verifier, state)
    const redirectUri = `http://${CALLBACK_HOST}:${port}${CALLBACK_PATH}`
    const url = new URL('/oauth', AUTH_BASE)
    url.search = new URLSearchParams({
      client_id: CLIENT_ID,
      response_type: 'code',
      scope: 'ai-account',
      state,
      redirect_uri: redirectUri,
      code_challenge: challenge,
      code_challenge_method: 'S256',
    }).toString()
    await this.writePrivate(this.initFile, { state, verifier, redirectUri, port })
    const timeout = setTimeout(() => server.close(), 5 * 60_000)
    timeout.unref()
    server.once('close', () => clearTimeout(timeout))
    return { authorizeUrl: url.toString(), port }
  }

  /** Exchanges the one-time callback code without returning any token material. */
  async exchange(): Promise<void> {
    const callback = await this.readJson<OAuthCallback>(this.callbackFile)
    const init = await this.readJson<{ state: string; verifier: string; redirectUri: string }>(this.initFile)
    if (callback.state !== init.state || typeof callback.code !== 'string' || callback.code === '' || callback.code_verifier !== init.verifier) {
      throw new Error('OAuth callback validation failed; restart Testnet authorization')
    }
    const response = await this.post('/oauth/v1/public/access_token', {
      client_id: CLIENT_ID,
      code: callback.code,
      code_verifier: init.verifier,
    })
    const result = object(response.result ?? response)
    const token = result.access_token
    const refresh = result.refresh_token
    if (typeof token !== 'string' || typeof refresh !== 'string') throw new Error('Testnet OAuth token exchange returned no token')
    const stored: OAuthToken = {
      access_token: token,
      refresh_token: refresh,
      expires_in: number(result.expires_in, 86_400),
      refresh_token_expires_in: number(result.refresh_token_expires_in, 2_592_000),
      token_type: typeof result.token_type === 'string' ? result.token_type : 'bearer',
      created_at: Math.floor(Date.now() / 1000),
      env: 'testnet',
    }
    await this.writePrivate(this.tokenFile, stored)
  }

  /** Lists available AI sub-accounts, withholding all credentials from output. */
  async accounts(): Promise<AiAccountSummary[]> {
    const token = await this.validToken()
    const response = await this.get('/oauth/v1/resource/restrict/ai_accounts', token)
    const result = object(response.result ?? response)
    const accounts = Array.isArray(response.result) ? response.result : result.accounts
    if (!Array.isArray(accounts)) throw new Error('Testnet OAuth returned an invalid AI sub-account list')
    return accounts.map((entry) => {
      const row = object(entry)
      return {
        sub_member_id: String(row.sub_member_id ?? ''),
        nickname: String(row.nickname ?? 'Unnamed account'),
      }
    }).filter((account) => account.sub_member_id !== '')
  }

  /** Fetches only the user-selected Testnet account and stores its API key pair privately. */
  async selectAccount(subMemberId: string): Promise<void> {
    if (!/^\d{1,24}$/.test(subMemberId)) throw new Error('sub_member_id must contain 1–24 digits')
    const token = await this.validToken()
    const response = await this.get(`/oauth/v1/resource/restrict/ai_accounts?sub_member_id=${encodeURIComponent(subMemberId)}`, token)
    const account = accountFrom(response)
    await this.saveAccount(account)
  }

  /** Creates an AI sub-account only when explicitly requested by the user. */
  async createAccount(): Promise<void> {
    const token = await this.validToken()
    const response = await this.get('/oauth/v1/resource/restrict/ai_accounts?is_create=true', token)
    const account = accountFrom(response)
    await this.saveAccount(account)
  }

  private async saveAccount(account: Record<string, unknown>): Promise<void> {
    const apiKey = account.api_key
    const apiSecret = account.api_secret
    if (typeof apiKey !== 'string' || typeof apiSecret !== 'string') {
      const fields = Object.keys(account).sort().join(',') || '(none)'
      throw new Error(`Selected Testnet account response has no API credentials; fields: ${fields}`)
    }
    const existing = await this.readOptionalJson<Record<string, unknown>>(this.credentialsFile)
    await this.writePrivate(this.credentialsFile, { ...existing, apiKey, apiSecret, env: 'testnet' })
  }

  private async validToken(): Promise<string> {
    let token = await this.readJson<OAuthToken>(this.tokenFile)
    const now = Math.floor(Date.now() / 1000)
    if (token.env !== 'testnet') throw new Error('Refusing to use a non-Testnet OAuth token')
    if (now - token.created_at >= token.expires_in - 60) {
      if (now - token.created_at >= token.refresh_token_expires_in) throw new Error('Testnet OAuth refresh token expired; authorize again')
      const response = await this.post('/oauth/v1/public/refresh_token', { client_id: CLIENT_ID, refresh_token: token.refresh_token })
      const result = object(response.result ?? response)
      if (typeof result.access_token !== 'string' || typeof result.refresh_token !== 'string') throw new Error('Testnet OAuth token refresh failed')
      token = {
        ...token,
        access_token: result.access_token,
        refresh_token: result.refresh_token,
        expires_in: number(result.expires_in, token.expires_in),
        refresh_token_expires_in: number(result.refresh_token_expires_in, token.refresh_token_expires_in),
        created_at: now,
      }
      await this.writePrivate(this.tokenFile, token)
    }
    return token.access_token
  }

  private async listen(verifier: string, state: string): Promise<{ server: ReturnType<typeof createServer>; port: number }> {
    for (let port = CALLBACK_PORT_START; port <= CALLBACK_PORT_START + 10; port += 1) {
      const server = createServer(async (request, response) => {
        const url = new URL(request.url ?? '/', `http://${CALLBACK_HOST}`)
        if (url.pathname !== CALLBACK_PATH) {
          response.writeHead(404).end()
          return
        }
        if (url.searchParams.get('state') !== state || url.searchParams.has('error')) {
          await this.writePrivate(this.callbackFile, { error: 'state_mismatch' })
          response.writeHead(403, { 'content-type': 'text/plain; charset=utf-8' }).end('Authorization failed. Return to the plugin setup.')
          server.close()
          return
        }
        const code = url.searchParams.get('code')
        if (!code) {
          response.writeHead(400).end('Authorization code missing.')
          return
        }
        await this.writePrivate(this.callbackFile, { code, state, code_verifier: verifier })
        response.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' }).end('Testnet authorization received. You can close this page.')
        server.close()
      })
      const bound = await new Promise<boolean>((resolve) => {
        server.once('error', () => {
          server.close()
          resolve(false)
        })
        server.listen(port, CALLBACK_HOST, () => resolve(true))
      })
      if (bound) return { server, port }
    }
    throw new Error(`Could not bind a loopback port between ${CALLBACK_PORT_START} and ${CALLBACK_PORT_START + 10}`)
  }

  private async post(path: string, body: Record<string, string>): Promise<OAuthResponse> {
    const encoded = new URLSearchParams(body).toString()
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded', accept: 'application/json' },
      body: encoded,
      signal: AbortSignal.timeout(15_000),
      redirect: 'error',
    })
    return this.unwrap(response)
  }

  private async get(path: string, token: string): Promise<OAuthResponse> {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { accept: 'application/json', authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(15_000),
      redirect: 'error',
    })
    return this.unwrap(response)
  }

  private async unwrap(response: Response): Promise<OAuthResponse> {
    const payload = object(await response.json()) as OAuthResponse
    const code = payload.retCode ?? payload.ret_code ?? 0
    if (!response.ok || code !== 0) {
      const message = String(payload.retMsg ?? payload.ret_msg ?? 'request failed')
      throw new Error(`Bybit Testnet OAuth failed (${String(code)}): ${message}`)
    }
    return payload
  }

  private async readJson<T>(file: string): Promise<T> {
    return JSON.parse(await readFile(file, 'utf8')) as T
  }

  private async readOptionalJson<T extends Record<string, unknown>>(file: string): Promise<T> {
    try { return await this.readJson<T>(file) } catch { return {} as T }
  }

  private async writePrivate(file: string, value: unknown): Promise<void> {
    await mkdir(dirname(file), { recursive: true, mode: 0o700 })
    const temporary = `${file}.tmp-${process.pid}`
    await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 })
    await chmod(temporary, 0o600)
    await rename(temporary, file)
  }
}

function object(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function accountFrom(response: OAuthResponse): Record<string, unknown> {
  const result = response.result ?? response
  if (Array.isArray(result)) return object(result[0])
  const record = object(result)
  const accounts = record.accounts
  return Array.isArray(accounts) ? object(accounts[0]) : object(accounts ?? record)
}

function number(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : fallback
}
