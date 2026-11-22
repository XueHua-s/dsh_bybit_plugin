import { backgroundLoopPrompt } from '../prompts/bybit-quant/background-loop-v4.js'

/** Narrow, runtime-checked contract for the optional DSH Agent service. */
export type ModelSelection = { provider: string, model: string, reasoningEffort?: string }
type AgentMessage = { content: Array<{ type: 'text', text: string }>, source: { kind: 'my-plugin' } }
export type ScopedAgentContext = {
  tools: { restrict(filter: { allow: readonly string[] }): unknown }
  systemPrompt: { section(section: { name: string, order: number, text: string }): unknown }
}
export type Agent = {
  followup(message: AgentMessage): void
  cancel(cause: { kind: 'disposed' }): void
  whenIdle(): Promise<void>
}
export type AgentHandle = { agent: Agent, dispose(): Promise<void> }
export type AgentServices = {
  agents: {
    create(options: {
      sessionId: string
      agentOptions: ModelSelection & { maxTokens: number }
      signal?: AbortSignal
      setup(context: ScopedAgentContext): void
    }): Promise<AgentHandle>
  }
  agentDefaultModel: { currentSelection(): ModelSelection }
}

/** Keep the model turn inside its explicit market-reading/simulated-decision capability. */
export const AI_LOOP_TOOL_ALLOWLIST = [
  'quant_brief',
  'quant_decide_background',
  'quant_review',
  'quant_signals',
  'bybit_market',
  'bybit_instruments',
  'quant_get_market_snapshot',
] as const

export function configureBackgroundAgent(context: ScopedAgentContext, cycleId: string): void {
  context.tools.restrict({ allow: AI_LOOP_TOOL_ALLOWLIST })
  context.systemPrompt.section({
    name: 'bybit-quant:background-loop-v4',
    order: 620,
    text: backgroundLoopPrompt(cycleId),
  })
}

export function isAgentServices(value: unknown): value is AgentServices {
  if (!isRecord(value)) return false
  const agents = value.agents
  const defaultModel = value.agentDefaultModel
  return isRecord(agents) && typeof agents.create === 'function'
    && isRecord(defaultModel) && typeof defaultModel.currentSelection === 'function'
}

export function safeSelection(services: AgentServices): ModelSelection | undefined {
  try {
    const selection = services.agentDefaultModel.currentSelection()
    if (typeof selection.provider !== 'string' || selection.provider.trim() === ''
      || typeof selection.model !== 'string' || selection.model.trim() === '') return undefined
    return {
      provider: selection.provider.trim(),
      model: selection.model.trim(),
      ...(typeof selection.reasoningEffort === 'string' ? { reasoningEffort: selection.reasoningEffort } : {}),
    }
  } catch {
    return undefined
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
