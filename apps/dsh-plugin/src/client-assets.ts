/** Static translations and styles for the browser panel. */
export const zh = {
      panel: 'Bybit 量化',
      title: 'Bybit 量化面板',
      subtitle: '实时行情 · 策略回测 · 模拟盘',
      symbol: '交易对',
      category: '市场',
      interval: '周期',
      refresh: '刷新',
      updated: '更新于',
      stale: '数据可能已过期',
      price: '最新价',
      change24h: '24h 涨跌',
      high24h: '24h 最高',
      low24h: '24h 最低',
      volume24h: '24h 成交额',
      funding: '资金费率',
      writesUnavailable: '交易所写入不可用',
      keysOn: 'API Key 已配置',
      keysOff: '未配置 API Key',
      envLive: '主网',
      envDemo: '模拟交易',
      envTestnet: '测试网',
      paper: '模拟盘账本',
      balance: '可用现金',
      equity: '总权益',
      totalReturn: '累计收益',
      positions: '持仓',
      noPositions: '暂无持仓',
      recentTrades: '最近成交',
      noTrades: '暂无成交',
      backtest: '最近回测',
      noBacktest: '还没有回测记录。在对话里让 Agent 调用 quant_backtest，例如「用 ma_cross 在 BTCUSDT 1h 上回测 500 根 K 线」。',
      strategy: '策略',
      signal: '当前信号',
      long: '持多',
      flat: '空仓',
      mReturn: '策略收益',
      mBuyHold: '买入持有',
      mDrawdown: '最大回撤',
      mWinRate: '胜率',
      mTrades: '交易次数',
      mSharpe: 'Sharpe',
      mFees: '费用拖累',
      captionBars: '根 K 线',
      chartAria: 'K 线图，含 20 与 50 周期均线',
      hint: '面板只读。交易工具只生成预览；交易所下单、撤单和自动化执行目前不可用。模拟盘仅更新合成账本。',
      errorFetch: '无法读取面板数据',
      errorRoute: '连不上 Host 的 /api/bybit-quant 面板接口。请刷新页面确认已登录，并确认插件已启用。',
      loading: '加载中…',
      empty: '暂无数据',
      colSymbol: '合约',
      colQty: '数量',
      colAvg: '均价',
      colMark: '标记价',
      colPnl: '浮动盈亏',
      colSide: '方向',
      colPrice: '价格',
      colTime: '时间',
      sideBuy: '买入',
      sideSell: '卖出',
      aiTitle: 'AI 模拟决策',
      aiSub: '仅记录模拟观点，不提交交易所订单',
      aiEquity: 'AI 模拟权益',
      aiReturn: 'AI 累计',
      aiHitRate: '命中率',
      aiBrier: 'Brier',
      aiNoDecision: '还没有 AI 决策。在对话里让 Agent 先跑 quant_brief，再用 quant_decide 记录观点。',
      aiLast: '最新决策',
      aiOpen: 'AI 模拟持仓',
      aiNoOpen: 'AI 空仓',
      aiClosed: '已平',
      aiCalibration: '置信度校准',
      aiLimits: '风控',
      aiRiskPerTrade: '单笔风险',
      aiMaxOpen: '最多持仓',
      aiConfidence: '信心',
      aiR: 'R 倍数',
      aiStatusOpen: '模拟持仓中',
      aiStatusClosed: '模拟已平仓',
      aiStatusFlat: '空仓',
      aiStatusRejected: '被风控拒绝',
      aiActionLong: '做多',
      aiActionShort: '做空',
      aiActionFlat: '不交易',
      readinessTitle: '运行边界',
      readinessAutomation: '自动化模式',
      readinessConversationOnly: '仅对话触发',
      readinessBackground: '后台循环',
      readinessNotRunning: '未运行',
      readinessAuthority: '执行权威',
      readinessUnavailable: '交易所写入不可用（执行器未实现）',
      readinessAccount: '账户就绪',
      readinessUnknown: '未知',
      readinessZeroEquity: '权益为零',
      readinessNotChecked: '尚未检查',
      readinessHint: '当前没有后台 AI 循环。交易工具只提供预览，不能提交真实订单；账户状态、订单对账与故障恢复也未完成。OAuth、API Key 或正常行情不代表执行已就绪。',
}



export const en = {
      panel: 'Bybit',
      title: 'Bybit quant panel',
      subtitle: 'Live market · backtests · paper book',
      symbol: 'Symbol',
      category: 'Market',
      interval: 'Interval',
      refresh: 'Refresh',
      updated: 'Updated',
      stale: 'Data may be stale',
      price: 'Last price',
      change24h: '24h change',
      high24h: '24h high',
      low24h: '24h low',
      volume24h: '24h turnover',
      funding: 'Funding',
      writesUnavailable: 'Exchange writes unavailable',
      keysOn: 'API key set',
      keysOff: 'No API key',
      envLive: 'Mainnet',
      envDemo: 'Demo',
      envTestnet: 'Testnet',
      paper: 'Paper book',
      balance: 'Free cash',
      equity: 'Equity',
      totalReturn: 'Total return',
      positions: 'Positions',
      noPositions: 'No open position',
      recentTrades: 'Recent fills',
      noTrades: 'No fills yet',
      backtest: 'Last backtest',
      noBacktest: 'No backtest yet. Ask the agent to run quant_backtest, for example "backtest ma_cross on BTCUSDT 1h over 500 candles".',
      strategy: 'Strategy',
      signal: 'Signal',
      long: 'Long',
      flat: 'Flat',
      mReturn: 'Strategy',
      mBuyHold: 'Buy & hold',
      mDrawdown: 'Max drawdown',
      mWinRate: 'Win rate',
      mTrades: 'Trades',
      mSharpe: 'Sharpe',
      mFees: 'Fee drag',
      captionBars: 'candles',
      chartAria: 'Candlestick chart with 20 and 50 period moving averages',
      hint: 'Read-only panel. The trade tool creates previews only; exchange orders, cancels, and automated execution are unavailable. Internal paper updates a synthetic book.',
      errorFetch: 'Cannot read panel data',
      errorRoute: 'The Host route /api/bybit-quant is unreachable. Reload the page to confirm you are signed in, and check that the plugin is enabled.',
      loading: 'Loading…',
      empty: 'No data',
      colSymbol: 'Contract',
      colQty: 'Qty',
      colAvg: 'Avg',
      colMark: 'Mark',
      colPnl: 'Unrealized',
      colSide: 'Side',
      colPrice: 'Price',
      colTime: 'Time',
      sideBuy: 'Buy',
      sideSell: 'Sell',
      aiTitle: 'AI simulated decisions',
      aiSub: 'Simulated track only; no exchange orders are submitted',
      aiEquity: 'AI simulated equity',
      aiReturn: 'AI return',
      aiHitRate: 'Hit rate',
      aiBrier: 'Brier',
      aiNoDecision: 'No AI decision yet. Ask the agent to run quant_brief, then record a view with quant_decide.',
      aiLast: 'Latest decision',
      aiOpen: 'AI simulated positions',
      aiNoOpen: 'AI is flat',
      aiClosed: 'closed',
      aiCalibration: 'Calibration',
      aiLimits: 'Risk',
      aiRiskPerTrade: 'per trade',
      aiMaxOpen: 'max open',
      aiConfidence: 'confidence',
      aiR: 'R',
      aiStatusOpen: 'simulated open',
      aiStatusClosed: 'simulated closed',
      aiStatusFlat: 'flat',
      aiStatusRejected: 'risk-rejected',
      aiActionLong: 'long',
      aiActionShort: 'short',
      aiActionFlat: 'flat',
      readinessTitle: 'Operating boundary',
      readinessAutomation: 'Automation',
      readinessConversationOnly: 'Conversation-triggered only',
      readinessBackground: 'Background loop',
      readinessNotRunning: 'Not running',
      readinessAuthority: 'Execution authority',
      readinessUnavailable: 'Exchange writes unavailable (executor not implemented)',
      readinessAccount: 'Account readiness',
      readinessUnknown: 'Unknown',
      readinessZeroEquity: 'Zero equity',
      readinessNotChecked: 'Not checked',
      readinessHint: 'No background AI loop is running. The trade tool only previews intent and cannot submit real orders; account state, order reconciliation, and recovery are not complete. OAuth, API keys, or healthy market data do not mean execution is ready.',
}



export const CSS = `
.bq-root { box-sizing: border-box; padding: calc(var(--dsh-frame-top-clearance, 16px) + 12px) 28px 64px;
  max-width: 1180px; margin: 0 auto; color: var(--dsw-alias-label-primary); font-size: 13px; line-height: 1.5; }
.bq-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 4px; }
.bq-title { margin: 0; font-size: 18px; font-weight: 600; }
.bq-sub { color: var(--dsw-alias-label-tertiary); font-size: 12px; margin: 0 0 16px; }
.bq-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-left: auto; align-items: center; }
.bq-badge { font-size: 11px; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--dsw-alias-border-l2);
  color: var(--dsw-alias-label-secondary); white-space: nowrap; }
.bq-badge-good { color: var(--dsw-alias-state-success-primary); border-color: var(--dsw-alias-state-success-primary); }
.bq-badge-warn { color: var(--dsw-alias-state-warn-primary); border-color: var(--dsw-alias-state-warn-primary); }
.bq-button { font: inherit; font-size: 12px; color: var(--dsw-alias-label-primary); background: var(--dsw-alias-bg-layer-2);
  border: 1px solid var(--dsw-alias-border-l2); border-radius: 8px; padding: 5px 12px; cursor: pointer; }
.bq-button:hover { background: var(--dsw-alias-interactive-bg-hover); }
.bq-button:focus-visible { outline: 2px solid var(--dsw-alias-brand-primary); outline-offset: 1px; }
.bq-controls { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 14px; }
.bq-field { display: flex; align-items: center; gap: 6px; }
.bq-label { color: var(--dsw-alias-label-tertiary); font-size: 12px; }
.bq-input { font: inherit; color: var(--dsw-alias-label-primary); background: var(--dsw-alias-bg-layer-2);
  border: 1px solid var(--dsw-alias-border-l2); border-radius: 8px; padding: 5px 10px; width: 120px; }
.bq-tabs { display: inline-flex; gap: 2px; padding: 2px; background: var(--dsw-alias-bg-layer-2); border-radius: 9px; }
.bq-tab { font: inherit; font-size: 12px; color: var(--dsw-alias-label-secondary); background: transparent; border: 0;
  border-radius: 7px; padding: 4px 10px; cursor: pointer; }
.bq-tab[aria-pressed="true"] { background: var(--dsw-alias-bg-layer-1); color: var(--dsw-alias-label-primary); box-shadow: 0 0 0 1px var(--dsw-alias-border-l2); }
.bq-card { background: var(--dsw-alias-bg-layer-1); border: 1px solid var(--dsw-alias-border-l1); border-radius: 12px; padding: 14px 16px; }
.bq-price-row { display: flex; align-items: flex-end; gap: 20px; flex-wrap: wrap; margin-bottom: 12px; }
.bq-price { font-size: 30px; font-weight: 600; letter-spacing: -0.5px; font-variant-numeric: tabular-nums; }
.bq-price-meta { display: flex; gap: 18px; flex-wrap: wrap; }
.bq-meta-item { display: flex; flex-direction: column; gap: 1px; }
.bq-meta-label { font-size: 11px; color: var(--dsw-alias-label-tertiary); }
.bq-meta-value { font-variant-numeric: tabular-nums; }
.bq-up { color: var(--dsw-alias-state-success-primary); }
.bq-down { color: var(--dsw-alias-state-error-primary); }
.bq-chart { display: block; width: 100%; height: auto; margin-top: 6px; }
.bq-grid-line { stroke: var(--dsw-alias-border-l1); stroke-width: 1; }
.bq-axis-text { fill: var(--dsw-alias-label-tertiary); font-size: 10px; font-variant-numeric: tabular-nums; }
.bq-legend { display: flex; gap: 14px; flex-wrap: wrap; color: var(--dsw-alias-label-tertiary); font-size: 11px; margin-top: 6px; }
.bq-legend-dot { display: inline-block; width: 8px; height: 2px; border-radius: 1px; vertical-align: middle; margin-right: 5px; }
.bq-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; margin-top: 12px; }
.bq-card-title { margin: 0 0 10px; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.bq-card-title span { color: var(--dsw-alias-label-tertiary); font-weight: 400; font-size: 11px; }
.bq-kv { display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: 10px; margin-bottom: 12px; }
.bq-kv-item { display: flex; flex-direction: column; gap: 1px; }
.bq-table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
.bq-table th { text-align: left; font-weight: 500; font-size: 11px; color: var(--dsw-alias-label-tertiary); padding: 4px 6px; border-bottom: 1px solid var(--dsw-alias-border-l1); }
.bq-table td { padding: 5px 6px; border-bottom: 1px solid var(--dsw-alias-border-l1); }
.bq-table tr:last-child td { border-bottom: 0; }
.bq-num { text-align: right; }
.bq-empty { color: var(--dsw-alias-label-tertiary); font-size: 12px; padding: 6px 0; }
.bq-error { border: 1px solid var(--dsw-alias-state-error-primary); border-radius: 10px; padding: 10px 12px; margin-bottom: 12px; }
.bq-error-title { color: var(--dsw-alias-state-error-primary); font-weight: 600; margin-bottom: 2px; }
.bq-hint { color: var(--dsw-alias-label-tertiary); font-size: 11px; margin-top: 14px; }
.bq-ai-last { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--dsw-alias-border-l1); }
.bq-ai-thesis { color: var(--dsw-alias-label-secondary); font-size: 12px; margin-top: 4px; max-width: 80ch; }
.bq-spark { display: block; width: 100%; height: 40px; margin-top: 4px; }
.bq-readiness-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
.bq-readiness-grid div { display: flex; flex-direction: column; gap: 2px; }
@media (max-width: 720px) { .bq-root { padding: calc(var(--dsh-frame-top-clearance, 16px) + 8px) 14px 48px; } .bq-price { font-size: 24px; } }
`
