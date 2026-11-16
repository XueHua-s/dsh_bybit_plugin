/**
 * Trust-boundary helpers for news, GitHub material and agent-provided text.
 * These values are evidence only and must never become executable instructions.
 */
export interface UntrustedText {
  text: string
  source: 'news' | 'github' | 'agent' | 'unknown'
  receivedAt: number
  trusted: false
}

const INJECTION_PATTERNS = [
  /ignore\s+(all\s+)?previous\s+instructions/i,
  /disregard\s+(the\s+)?system\s+prompt/i,
  /reveal\s+(the\s+)?(api|secret|credential|token)/i,
  /execute\s+(this\s+)?(script|command|code)/i,
  /system\s*message\s*:/i,
]

/** Normalize untrusted content and retain its provenance for audit logs. */
export function markUntrusted(value: unknown, source: UntrustedText['source'] = 'unknown'): UntrustedText {
  const text = typeof value === 'string' ? value.normalize('NFKC').slice(0, 20_000) : String(value ?? '').slice(0, 20_000)
  return { text, source, receivedAt: Date.now(), trusted: false }
}

/** Return a safe evidence envelope; callers must inspect flags before use. */
export function inspectUntrusted(value: UntrustedText): { accepted: false, reason: 'prompt-injection' | 'empty' | 'untrusted' } | { accepted: true, evidence: string } {
  if (value.text.trim() === '') return { accepted: false, reason: 'empty' }
  if (INJECTION_PATTERNS.some(pattern => pattern.test(value.text))) return { accepted: false, reason: 'prompt-injection' }
  return { accepted: true, evidence: value.text }
}

/** Remove control characters before evidence is written to a prompt or log. */
export function evidenceText(value: unknown, source: UntrustedText['source'] = 'unknown'): string {
  const inspected = inspectUntrusted(markUntrusted(value, source))
  return inspected.accepted ? inspected.evidence : `[untrusted evidence rejected: ${inspected.reason}]`
}
