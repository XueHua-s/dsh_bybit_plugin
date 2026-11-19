/** Fixed Bybit V5 endpoints and interval metadata. */
/** Endpoint per trading environment. */
export const ENDPOINTS = {
  live: 'https://api.bybit.com',
  demo: 'https://api-demo.bybit.com',
  testnet: 'https://api-testnet.bybit.com',
} as const

/** Public market endpoints by environment; product runtime still defaults to live data. */
export const MARKET_ENDPOINTS = {
  live: 'https://api.bybit.com',
  demo: 'https://api-demo.bybit.com',
  testnet: 'https://api-testnet.bybit.com',
} as const

/** Backward-compatible default for ordinary product clients. */
export const MARKET_ENDPOINT = 'https://api.bybit.com'

/** Bybit kline interval codes, in ascending order. */
export const INTERVALS = ['1', '3', '5', '15', '30', '60', '120', '240', '360', '720', 'D', 'W', 'M'] as const

/** Human spellings accepted in tool arguments. */
export const INTERVAL_ALIASES: Record<string, string> = {
  '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
  '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
  '1d': 'D', '1w': 'W', '1M': 'M',
}

/** Bar duration in ms for lookups that need annualisation. */
export const INTERVAL_MS: Record<string, number> = {
  '1': 60_000, '3': 180_000, '5': 300_000, '15': 900_000, '30': 1_800_000,
  '60': 3_600_000, '120': 7_200_000, '240': 14_400_000, '360': 21_600_000,
  '720': 43_200_000, D: 86_400_000, W: 604_800_000, M: 2_592_000_000,
}
