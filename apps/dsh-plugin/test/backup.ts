/** Isolated checksum-backed backup and restore regression. */
import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createBackup, restoreBackup } from '../src/lib/backup.ts'
import { createStore } from '../dist/lib/state.js'

const directory = await mkdtemp(join(tmpdir(), 'bybit-quant-backup-'))
try {
  const stateFile = join(directory, 'state.json')
  const store = createStore({ file: stateFile, startingBalance: 1000 })
  store.mutate((state) => {
    state.watchlist = ['BTCUSDT']
    state.paper.trades.push({
      time: 1, side: 'buy', category: 'linear', symbol: 'BTCUSDT',
      qty: 0.01, price: 60000, feeUsd: 0.1, note: 'isolated recovery fixture',
    })
    state.ai = {
      version: 1, createdAt: 1, startEquity: 1000, equity: 1000,
      peakEquity: 1000, maxDrawdownPct: 0, feesPaidUsd: 0,
      dayKey: '2026-11-17', dayStartEquity: 1000,
      positions: {}, decisions: [], equityCurve: [],
    }
    state.auditMarker = { id: 'audit-fixture-1', appendOnly: true }
  })

  const manifest = await createBackup(stateFile)
  const manifestFile = join(directory, 'state.json.bak.manifest.json')
  await writeFile(stateFile, '{"version":1,"paper":{}}\n')
  await restoreBackup(manifestFile)
  const restored = createStore({ file: stateFile, startingBalance: 1000 }).get()

  assert.deepEqual(restored.watchlist, ['BTCUSDT'])
  assert.equal(restored.paper.trades[0]?.symbol, 'BTCUSDT')
  assert.equal(restored.ai?.version, 1)
  assert.deepEqual(restored.auditMarker, { id: 'audit-fixture-1', appendOnly: true })
  assert.equal((await readFile(stateFile, 'utf8')).includes('isolated recovery fixture'), true)

  await writeFile(manifest.backup, 'tampered backup')
  await assert.rejects(restoreBackup(manifestFile), /backup checksum mismatch; refusing restore/)
  console.log('PASS backup restore preserves strategy, paper trade, AI track and audit marker; checksum tampering refused')
} finally {
  await rm(directory, { recursive: true, force: true })
}
