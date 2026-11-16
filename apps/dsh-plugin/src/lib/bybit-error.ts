/** Error carrying Bybit's business code so callers can report it verbatim. */
export class BybitError extends Error {
  readonly retCode: number | undefined
  readonly retMsg: string | undefined
  readonly endpoint: string | undefined
  readonly status: number | undefined

  constructor(message: string, detail: { retCode?: number, retMsg?: string, endpoint?: string, status?: number } = {}) {
    super(message)
    this.name = 'BybitError'
    this.retCode = detail.retCode
    this.retMsg = detail.retMsg
    this.endpoint = detail.endpoint
    this.status = detail.status
  }
}
