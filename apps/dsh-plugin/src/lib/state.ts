/**
 * The plugin's own small JSON store: the paper book, the last backtest, the
 * last evaluated signal, the AI track, and the user's watchlist. It is shared by
 * the agent tools and the Web panel route.
 *
 * The file lives under the DSH home directory (not the workspace) so a user's
 * project never receives trading state, and every write is atomic: a reader
 * either sees the previous document or the next one.
 */
import { copyFileSync, existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'
import type { DecisionTrack } from './ai-types.js'

/** Maximum paper trades and notes retained in the document. */
const MAX_TRADES = 200
const MAX_NOTES = 50

/** One simulated paper position. */
export interface PaperPosition {
  category: string
  symbol: string
  qty: number
  avgPrice: number
  openedAt: number
}

/** One simulated fill. */
export interface PaperTrade {
  time: number
  side: 'buy' | 'sell'
  category: string
  symbol: string
  qty: number
  price: number
  feeUsd: number
  realizedPnlUsd?: number
  note: string
}

/** The simulated book. */
export interface PaperBook {
  currency: string
  balance: number
  startingBalance: number
  realizedPnlUsd: number
  feesPaidUsd: number
  positions: Record<string, PaperPosition>
  trades: PaperTrade[]
}

/** The complete persisted document. Unknown fields from newer versions survive. */
export interface StateDocument {
  version: 1
  createdAt: number
  updatedAt: number
  paper: PaperBook
  lastBacktest: unknown
  lastSignal: unknown
  notes: string[]
  /** AI paper track and append-only decision journal. */
  ai?: DecisionTrack
  watchlist?: string[]
  [key: string]: unknown
}

/** Store handle returned by {@link createStore}. */
export interface Store {
  /** Current document; mutate only through `mutate`. */
  get(): StateDocument
  /** Apply one change and persist it. */
  mutate<T>(change: (state: StateDocument) => T): T
  /** Path of the document, for reporting. */
  readonly file: string
}

/** Directory that holds the state file. */
export function defaultStateDir(): string {
  const home = process.env.DSH_HOME !== undefined && process.env.DSH_HOME !== '' ? process.env.DSH_HOME : join(homedir(), '.dsh')
  return join(home, 'bybit-quant')
}

/** Fresh document for a new paper book. */
export function initialState(startingBalance: number, now = Date.now()): StateDocument {
  return {
    version: 1,
    createdAt: now,
    updatedAt: now,
    paper: {
      currency: 'USDT',
      balance: startingBalance,
      startingBalance,
      realizedPnlUsd: 0,
      feesPaidUsd: 0,
      positions: {},
      trades: [],
    },
    lastBacktest: null,
    lastSignal: null,
    notes: [],
  }
}

/** Open (or create) the state document. */
export function createStore({ file, startingBalance }: { file: string, startingBalance: number }): Store {
  assertDocument(file, startingBalance)
  let state = initialState(startingBalance)

  /** Read the file once, repairing a missing or malformed document. */
  function load(): void {
    if (!existsSync(file)) return
    try {
      const parsed = JSON.parse(readFileSync(file, 'utf8')) as Partial<StateDocument> | null
      if (parsed?.version !== 1 || typeof parsed.paper !== 'object' || parsed.paper === null) {
        throw new Error('unexpected document shape')
      }
      state = normalize(parsed, startingBalance)
    } catch (error) {
      // Keep the unreadable file for inspection instead of destroying it.
      try {
        renameSync(file, `${file}.corrupt-${Date.now()}`)
      } catch {
        // Renaming is best effort; a fresh document still opens.
      }
      state = initialState(startingBalance)
      state.notes.push(`state file was unreadable (${(error as Error).message}); started a fresh book`)
    }
  }

  /** Persist the document through a temporary file and a rename. */
  function save(): void {
    mkdirSync(dirname(file), { recursive: true })
    const temporary = `${file}.tmp-${String(process.pid)}`
    const next = `${JSON.stringify(state, null, 2)}\n`
    writeFileSync(temporary, next, { encoding: 'utf8', mode: 0o600 })
    if (existsSync(file)) {
      const backupTemporary = `${file}.bak.tmp-${String(process.pid)}`
      copyFileSync(file, backupTemporary)
      renameSync(backupTemporary, `${file}.bak`)
    }
    renameSync(temporary, file)
  }

  load()

  return {
    get(): StateDocument {
      return state
    },
    mutate<T>(change: (state: StateDocument) => T): T {
      const result = change(state)
      state.updatedAt = Date.now()
      state.paper.trades = state.paper.trades.slice(-MAX_TRADES)
      state.notes = state.notes.slice(-MAX_NOTES)
      save()
      return result
    },
    get file(): string {
      return file
    },
  }
}

/** Ensure the directory exists before the first write, and report a bad balance. */
function assertDocument(file: string, startingBalance: number): void {
  if (!Number.isFinite(startingBalance) || startingBalance <= 0) {
    throw new Error('paperBalanceUsd must be a positive number')
  }
  mkdirSync(dirname(file), { recursive: true })
}

/** Fill fields a previous document version may have omitted. */
function normalize(parsed: Partial<StateDocument>, startingBalance: number): StateDocument {
  const paper = (parsed.paper ?? {}) as Partial<PaperBook>
  return {
    // Keep fields this version does not know about (the AI track, the
    // watchlist) instead of rebuilding the document and losing them.
    ...parsed,
    version: 1,
    createdAt: Number(parsed.createdAt ?? Date.now()),
    updatedAt: Number(parsed.updatedAt ?? Date.now()),
    paper: {
      currency: paper.currency ?? 'USDT',
      balance: Number.isFinite(Number(paper.balance)) ? Number(paper.balance) : startingBalance,
      startingBalance: Number.isFinite(Number(paper.startingBalance)) ? Number(paper.startingBalance) : startingBalance,
      realizedPnlUsd: Number(paper.realizedPnlUsd ?? 0),
      feesPaidUsd: Number(paper.feesPaidUsd ?? 0),
      positions: typeof paper.positions === 'object' && paper.positions !== null ? paper.positions : {},
      trades: Array.isArray(paper.trades) ? paper.trades : [],
    },
    lastBacktest: parsed.lastBacktest ?? null,
    lastSignal: parsed.lastSignal ?? null,
    notes: Array.isArray(parsed.notes) ? parsed.notes : [],
  } as StateDocument
}
