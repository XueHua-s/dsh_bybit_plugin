import assert from 'node:assert/strict'
import { BybitClient, MARKET_ENDPOINTS } from '../dist/lib/bybit.js'

const testnet = new BybitClient({ env: 'testnet', marketEndpoint: MARKET_ENDPOINTS.testnet })
assert.equal(testnet.marketBase, 'https://api-testnet.bybit.com')
assert.equal(testnet.tradingBase, 'https://api-testnet.bybit.com')

const ordinary = new BybitClient({ env: 'testnet' })
assert.equal(ordinary.marketBase, 'https://api.bybit.com', 'product clients retain the live-market default')

console.log('ok public endpoint selection (no network requests)')
