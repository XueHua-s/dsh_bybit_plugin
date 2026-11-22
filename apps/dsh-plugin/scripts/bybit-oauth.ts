import { BybitOAuth, type OAuthEnvironment } from '../src/lib/bybit-oauth.ts'

const raw = process.argv.slice(2).filter(value => value !== '--')
const envArg = raw.find(value => value.startsWith('--env='))?.slice('--env='.length)
if (envArg !== undefined && envArg !== 'testnet' && envArg !== 'live') {
  throw new Error('--env must be testnet or live')
}
const env: OAuthEnvironment = envArg === 'live' ? 'live' : 'testnet'
const oauth = new BybitOAuth(undefined, env)
const [action, argument] = raw.filter(value => !value.startsWith('--env='))
const label = env === 'live' ? 'MAINNET' : 'TESTNET'

try {
  if (action === 'start') {
    const result = await oauth.start()
    console.log(`[${label}] Authorize Bybit ${env === 'live' ? 'Mainnet' : 'Testnet'}: ${result.authorizeUrl}`)
    console.log(`Callback listening on 127.0.0.1:${result.port}; finish authorization in your browser.`)
  } else if (action === 'exchange') {
    await oauth.exchange()
    console.log(`[${label}] OAuth token stored privately; no token values were printed.`)
  } else if (action === 'accounts') {
    const accounts = await oauth.accounts()
    console.log(JSON.stringify(accounts, null, 2))
    console.log(`Choose an account explicitly with: pnpm oauth -- ${env === 'live' ? '--env=live ' : ''}select <sub_member_id>`)
  } else if (action === 'select' && argument !== undefined) {
    await oauth.selectAccount(argument)
    console.log(`[${label}] Selected AI sub-account credentials stored privately; no secret values were printed.`)
    console.log(`Selected-account credentials file: ${oauth.credentialsFile}`)
  } else if (action === 'create') {
    await oauth.createAccount()
    console.log(`[${label}] AI sub-account created and credentials stored privately; no secret values were printed.`)
  } else {
    throw new Error('usage: pnpm oauth -- [--env=testnet|live] start|exchange|accounts|select <sub_member_id>|create')
  }
} catch (error) {
  console.error(error instanceof Error ? error.message : `${label} OAuth operation failed`)
  process.exitCode = 1
}
