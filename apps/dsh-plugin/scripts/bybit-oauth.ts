import { BybitTestnetOAuth } from '../src/lib/bybit-oauth.ts'

const oauth = new BybitTestnetOAuth()
const [action, argument] = process.argv.slice(2).filter(value => value !== '--')

try {
  if (action === 'start') {
    const result = await oauth.start()
    console.log(`[TESTNET] Authorize Bybit Testnet: ${result.authorizeUrl}`)
    console.log(`Callback listening on 127.0.0.1:${result.port}; finish authorization in your browser.`)
  } else if (action === 'exchange') {
    await oauth.exchange()
    console.log('[TESTNET] OAuth token stored privately; no token values were printed.')
  } else if (action === 'accounts') {
    const accounts = await oauth.accounts()
    console.log(JSON.stringify(accounts, null, 2))
    console.log('Choose an account explicitly with: pnpm oauth -- select <sub_member_id>')
  } else if (action === 'select' && argument !== undefined) {
    await oauth.selectAccount(argument)
    console.log('[TESTNET] Selected AI sub-account credentials stored privately; no secret values were printed.')
  } else if (action === 'create') {
    await oauth.createAccount()
    console.log('[TESTNET] AI sub-account created and credentials stored privately; no secret values were printed.')
  } else {
    throw new Error('usage: pnpm oauth -- start|exchange|accounts|select <sub_member_id>|create')
  }
} catch (error) {
  console.error(error instanceof Error ? error.message : 'Testnet OAuth operation failed')
  process.exitCode = 1
}
